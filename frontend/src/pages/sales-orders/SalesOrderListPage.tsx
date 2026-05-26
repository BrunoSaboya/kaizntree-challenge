import {
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  NumberInput,
  Pagination,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import "@mantine/dates/styles.css";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconPlus, IconX } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { zodResolver } from "mantine-form-zod-resolver";
import { z } from "zod";

import { productsApi } from "@/api/products";
import { stockApi } from "@/api/stock";
import { salesOrdersApi } from "@/api/orders";
import { PageHeader } from "@/components/common/PageHeader";
import { ORDER_STATUS_COLORS, ORDER_STATUS_LABELS } from "@/types/orders";
import { formatCurrency, formatDate } from "@/utils/formatters";

const schema = z.object({
  product: z.number({ required_error: "Product is required" }),
  stock: z.number({ required_error: "Stock entry is required" }),
  quantity: z.number().positive("Must be > 0"),
  price_per_unit: z.number().positive("Must be > 0"),
  order_date: z.date({ required_error: "Date is required" }),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

function NewSOModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [selectedProduct, setSelectedProduct] = useState<number | null>(null);

  const { data: products } = useQuery({
    queryKey: ["products", { page: 1 }],
    queryFn: () => productsApi.list({ page: 1, page_size: 100 }),
  });

  const { data: stockEntries } = useQuery({
    queryKey: ["stock", { product: selectedProduct }],
    queryFn: () => stockApi.list({ product: selectedProduct! }),
    enabled: !!selectedProduct,
  });

  const form = useForm<FormValues>({
    initialValues: { product: 0, stock: 0, quantity: 0, price_per_unit: 0, order_date: new Date(), notes: "" },
    validate: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      salesOrdersApi.create({
        ...values,
        order_date: values.order_date.toISOString().split("T")[0],
      } as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sales-orders"] });
      notifications.show({ title: "Created", message: "Sales order created as draft.", color: "green" });
      form.reset();
      setSelectedProduct(null);
      onClose();
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Failed to create sales order.", color: "red" });
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title="New Sales Order">
      <form onSubmit={form.onSubmit((v) => mutation.mutate(v))}>
        <Stack>
          <Select
            label="Product"
            placeholder="Select a product"
            data={(products?.results ?? []).map((p) => ({ value: String(p.id), label: `${p.name} (${p.sku})` }))}
            onChange={(v) => {
              const id = v ? parseInt(v) : 0;
              setSelectedProduct(id);
              form.setFieldValue("product", id);
              form.setFieldValue("stock", 0);
            }}
            error={form.errors.product}
            required
          />
          <Select
            label="Stock / Lot"
            placeholder={selectedProduct ? "Select a lot" : "Select a product first"}
            disabled={!selectedProduct}
            data={(stockEntries?.results ?? [])
              .filter((s) => parseFloat(s.quantity) > 0)
              .map((s) => ({
                value: String(s.id),
                label: `${s.identifier} (qty: ${s.quantity})`,
              }))}
            onChange={(v) => form.setFieldValue("stock", v ? parseInt(v) : 0)}
            error={form.errors.stock}
            required
          />
          <NumberInput label="Quantity" min={0.001} decimalScale={3} required {...form.getInputProps("quantity")} />
          <NumberInput label="Price per Unit ($)" min={0.0001} decimalScale={4} required {...form.getInputProps("price_per_unit")} />
          <DateInput label="Order Date" required {...form.getInputProps("order_date")} />
          <Textarea label="Notes" placeholder="Optional notes" {...form.getInputProps("notes")} />
          <Button type="submit" loading={mutation.isPending}>Create Draft</Button>
        </Stack>
      </form>
    </Modal>
  );
}

export default function SalesOrderListPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [opened, { open, close }] = useDisclosure(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["sales-orders", { page, status: statusFilter }],
    queryFn: () => salesOrdersApi.list({ page, status: statusFilter || undefined }),
  });

  const confirmMutation = useMutation({
    mutationFn: salesOrdersApi.confirm,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sales-orders"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["financials"] });
      notifications.show({ title: "Confirmed", message: "Sales order confirmed and stock decremented.", color: "green" });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "Failed to confirm order.";
      notifications.show({ title: "Error", message: msg, color: "red" });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: salesOrdersApi.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sales-orders"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      notifications.show({ title: "Cancelled", message: "Sales order cancelled.", color: "orange" });
    },
    onError: (err: any) => {
      notifications.show({ title: "Error", message: err?.response?.data?.detail || "Cannot cancel.", color: "red" });
    },
  });

  const totalPages = data ? Math.ceil(data.count / 20) : 1;

  return (
    <Stack>
      <PageHeader
        title="Sales Orders"
        action={<Button leftSection={<IconPlus size={16} />} onClick={open}>New Order</Button>}
      />

      <Group>
        <Select
          placeholder="Filter by status"
          data={[
            { value: "", label: "All statuses" },
            { value: "draft", label: "Draft" },
            { value: "confirmed", label: "Confirmed" },
            { value: "cancelled", label: "Cancelled" },
          ]}
          value={statusFilter}
          onChange={(v) => { setStatusFilter(v); setPage(1); }}
          clearable
          style={{ width: 180 }}
        />
      </Group>

      {isLoading ? (
        <Center h={200}><Loader /></Center>
      ) : (
        <Card shadow="sm" padding={0} radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Product</Table.Th>
                <Table.Th>Lot</Table.Th>
                <Table.Th ta="right">Qty</Table.Th>
                <Table.Th ta="right">Price/Unit</Table.Th>
                <Table.Th ta="right">Revenue</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th ta="center">Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.results.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={8}>
                    <Center py="xl"><Text c="dimmed">No sales orders yet.</Text></Center>
                  </Table.Td>
                </Table.Tr>
              ) : (
                data?.results.map((so: import("@/types/orders").SalesOrder) => (
                  <Table.Tr key={so.id}>
                    <Table.Td>
                      <Stack gap={0}>
                        <Text size="sm" fw={500}>{so.product_name}</Text>
                        <Badge size="xs" variant="light">{so.product_sku}</Badge>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      {so.stock_identifier ? (
                        <Badge variant="outline" size="sm">{so.stock_identifier}</Badge>
                      ) : "—"}
                    </Table.Td>
                    <Table.Td ta="right">{so.quantity}</Table.Td>
                    <Table.Td ta="right">{formatCurrency(so.price_per_unit)}</Table.Td>
                    <Table.Td ta="right" fw={500}>{formatCurrency(so.total_revenue)}</Table.Td>
                    <Table.Td c="dimmed" fz="sm">{formatDate(so.order_date)}</Table.Td>
                    <Table.Td>
                      <Badge color={ORDER_STATUS_COLORS[so.status]} variant="light">
                        {ORDER_STATUS_LABELS[so.status]}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group justify="center" gap="xs">
                        {so.status === "draft" && (
                          <>
                            <Button
                              size="xs"
                              color="green"
                              variant="light"
                              leftSection={<IconCheck size={14} />}
                              onClick={() => confirmMutation.mutate(so.id)}
                              loading={confirmMutation.isPending}
                            >
                              Confirm
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              leftSection={<IconX size={14} />}
                              onClick={() => cancelMutation.mutate(so.id)}
                              loading={cancelMutation.isPending}
                            >
                              Cancel
                            </Button>
                          </>
                        )}
                        {so.status === "confirmed" && (
                          <Button
                            size="xs"
                            color="orange"
                            variant="light"
                            leftSection={<IconX size={14} />}
                            onClick={() => cancelMutation.mutate(so.id)}
                            loading={cancelMutation.isPending}
                          >
                            Cancel
                          </Button>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
          {totalPages > 1 && (
            <Group justify="center" p="md">
              <Pagination total={totalPages} value={page} onChange={setPage} />
            </Group>
          )}
        </Card>
      )}

      <NewSOModal opened={opened} onClose={close} />
    </Stack>
  );
}
