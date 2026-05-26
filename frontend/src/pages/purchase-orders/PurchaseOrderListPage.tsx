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
  TextInput,
  Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import "@mantine/dates/styles.css";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconCheck,
  IconPlus,
  IconX,
} from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { zodResolver } from "mantine-form-zod-resolver";
import { z } from "zod";

import { productsApi } from "@/api/products";
import { purchaseOrdersApi } from "@/api/orders";
import { PageHeader } from "@/components/common/PageHeader";
import { ORDER_STATUS_COLORS, ORDER_STATUS_LABELS } from "@/types/orders";
import { formatCurrency, formatDate } from "@/utils/formatters";

const schema = z.object({
  product: z.number({ required_error: "Product is required" }),
  quantity: z.number().positive("Must be > 0"),
  cost_per_unit: z.number().positive("Must be > 0"),
  order_date: z.date({ required_error: "Date is required" }),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

function ConfirmPOModal({
  poId,
  opened,
  onClose,
}: {
  poId: number;
  opened: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [identifier, setIdentifier] = useState("");

  const mutation = useMutation({
    mutationFn: () => purchaseOrdersApi.confirm(poId, identifier),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["financials"] });
      notifications.show({ title: "Confirmed", message: "Purchase order confirmed and stock updated.", color: "green" });
      onClose();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "Failed to confirm order.";
      notifications.show({ title: "Error", message: msg, color: "red" });
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title="Confirm Purchase Order">
      <Stack>
        <Text size="sm" c="dimmed">
          Confirming this order will add the stock with the identifier below. You can use an existing lot
          identifier to add to existing stock, or a new one to create a new lot.
        </Text>
        <TextInput
          label="Stock / Lot Identifier"
          placeholder="e.g. LOT-2025-001"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
        />
        <Button
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!identifier}
          color="green"
        >
          Confirm & Add Stock
        </Button>
      </Stack>
    </Modal>
  );
}

function NewPOModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();

  const { data: products } = useQuery({
    queryKey: ["products", { page: 1 }],
    queryFn: () => productsApi.list({ page: 1, page_size: 100 }),
  });

  const form = useForm<FormValues>({
    initialValues: {
      product: 0,
      quantity: 0,
      cost_per_unit: 0,
      order_date: new Date(),
      notes: "",
    },
    validate: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      purchaseOrdersApi.create({
        ...values,
        order_date: values.order_date.toISOString().split("T")[0],
      } as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      notifications.show({ title: "Created", message: "Purchase order created as draft.", color: "green" });
      form.reset();
      onClose();
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Failed to create purchase order.", color: "red" });
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title="New Purchase Order">
      <form onSubmit={form.onSubmit((v) => mutation.mutate(v))}>
        <Stack>
          <Select
            label="Product"
            placeholder="Select a product"
            data={(products?.results ?? []).map((p) => ({ value: String(p.id), label: `${p.name} (${p.sku})` }))}
            onChange={(v) => form.setFieldValue("product", v ? parseInt(v) : 0)}
            error={form.errors.product}
            required
          />
          <NumberInput label="Quantity" min={0.001} decimalScale={3} required {...form.getInputProps("quantity")} />
          <NumberInput label="Cost per Unit ($)" min={0.0001} decimalScale={4} required {...form.getInputProps("cost_per_unit")} />
          <DateInput label="Order Date" required {...form.getInputProps("order_date")} />
          <Textarea label="Notes" placeholder="Optional notes" {...form.getInputProps("notes")} />
          <Button type="submit" loading={mutation.isPending}>Create Draft</Button>
        </Stack>
      </form>
    </Modal>
  );
}

export default function PurchaseOrderListPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [newOpened, { open: openNew, close: closeNew }] = useDisclosure(false);
  const [confirmPoId, setConfirmPoId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["purchase-orders", { page, status: statusFilter }],
    queryFn: () => purchaseOrdersApi.list({ page, status: statusFilter || undefined }),
  });

  const cancelMutation = useMutation({
    mutationFn: purchaseOrdersApi.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      notifications.show({ title: "Cancelled", message: "Purchase order cancelled.", color: "orange" });
    },
    onError: (err: any) => {
      notifications.show({ title: "Error", message: err?.response?.data?.detail || "Cannot cancel.", color: "red" });
    },
  });

  const totalPages = data ? Math.ceil(data.count / 20) : 1;

  return (
    <Stack>
      <PageHeader
        title="Purchase Orders"
        action={<Button leftSection={<IconPlus size={16} />} onClick={openNew}>New Order</Button>}
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
                <Table.Th ta="right">Qty</Table.Th>
                <Table.Th ta="right">Cost/Unit</Table.Th>
                <Table.Th ta="right">Total Cost</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th ta="center">Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.results.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7}>
                    <Center py="xl"><Text c="dimmed">No purchase orders yet.</Text></Center>
                  </Table.Td>
                </Table.Tr>
              ) : (
                data?.results.map((po: import("@/types/orders").PurchaseOrder) => (
                  <Table.Tr key={po.id}>
                    <Table.Td>
                      <Stack gap={0}>
                        <Text size="sm" fw={500}>{po.product_name}</Text>
                        <Badge size="xs" variant="light">{po.product_sku}</Badge>
                      </Stack>
                    </Table.Td>
                    <Table.Td ta="right">{po.quantity}</Table.Td>
                    <Table.Td ta="right">{formatCurrency(po.cost_per_unit)}</Table.Td>
                    <Table.Td ta="right" fw={500}>{formatCurrency(po.total_cost)}</Table.Td>
                    <Table.Td c="dimmed" fz="sm">{formatDate(po.order_date)}</Table.Td>
                    <Table.Td>
                      <Badge color={ORDER_STATUS_COLORS[po.status]} variant="light">
                        {ORDER_STATUS_LABELS[po.status]}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group justify="center" gap="xs">
                        {po.status === "draft" && (
                          <>
                            <Button
                              size="xs"
                              color="green"
                              variant="light"
                              leftSection={<IconCheck size={14} />}
                              onClick={() => setConfirmPoId(po.id)}
                            >
                              Confirm
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="light"
                              leftSection={<IconX size={14} />}
                              onClick={() => cancelMutation.mutate(po.id)}
                              loading={cancelMutation.isPending}
                            >
                              Cancel
                            </Button>
                          </>
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

      <NewPOModal opened={newOpened} onClose={closeNew} />
      {confirmPoId && (
        <ConfirmPOModal
          poId={confirmPoId}
          opened={!!confirmPoId}
          onClose={() => setConfirmPoId(null)}
        />
      )}
    </Stack>
  );
}
