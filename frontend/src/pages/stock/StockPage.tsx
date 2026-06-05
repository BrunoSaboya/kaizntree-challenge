import {
  Badge,
  Button,
  Card,
  Center,
  Drawer,
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
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconHistory, IconPlus } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useState } from "react";
import { zodResolver } from "mantine-form-zod-resolver";
import { z } from "zod";

import { stockApi, type StockMovement } from "@/api/stock";
import { productsApi } from "@/api/products";
import { PageHeader } from "@/components/common/PageHeader";
import { formatDate } from "@/utils/formatters";

const schema = z.object({
  product: z.number({ required_error: "Product is required" }),
  identifier: z.string().min(1, "Identifier is required"),
  quantity: z.number().positive("Must be greater than 0"),
  notes: z.string().optional(),
  expiry_date: z.date().nullable().optional(),
});

type FormValues = z.infer<typeof schema>;

function StockFormModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();

  const { data: products } = useQuery({
    queryKey: ["products", { page: 1 }],
    queryFn: () => productsApi.list({ page: 1, page_size: 100 }),
  });

  const form = useForm<FormValues>({
    initialValues: { product: 0, identifier: "", quantity: 0, notes: "", expiry_date: null },
    validate: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = {
        ...values,
        expiry_date: values.expiry_date ? dayjs(values.expiry_date).format("YYYY-MM-DD") : null,
      };
      return stockApi.create(payload as any);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      notifications.show({ title: "Success", message: "Stock entry added.", color: "green" });
      form.reset();
      onClose();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.identifier?.[0] || err?.response?.data?.detail || "Failed to add stock.";
      notifications.show({ title: "Error", message: msg, color: "red" });
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title="Add Stock">
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
          <TextInput
            label="Lot / Batch Identifier"
            placeholder="e.g. LOT-2025-001"
            required
            {...form.getInputProps("identifier")}
          />
          <DateInput
            label="Expiry Date"
            placeholder="No expiry"
            clearable
            valueFormat="MMM D, YYYY"
            {...form.getInputProps("expiry_date")}
          />
          <NumberInput
            label="Quantity"
            placeholder="e.g. 100"
            min={0.001}
            decimalScale={3}
            required
            {...form.getInputProps("quantity")}
          />
          <Textarea label="Notes" placeholder="Optional notes" {...form.getInputProps("notes")} />
          <Button type="submit" loading={mutation.isPending}>
            Add Stock
          </Button>
        </Stack>
      </form>
    </Modal>
  );
}

const MOVEMENT_COLORS: Record<string, string> = {
  PURCHASE_CONFIRMED: "teal",
  SALES_CONFIRMED: "red",
  SALES_CANCELLED: "orange",
  MANUAL_ADJUSTMENT: "blue",
};

const MOVEMENT_LABELS: Record<string, string> = {
  PURCHASE_CONFIRMED: "Purchase In",
  SALES_CONFIRMED: "Sale Out",
  SALES_CANCELLED: "Sale Cancelled",
  MANUAL_ADJUSTMENT: "Manual",
};

function MovementDrawer({
  stockId,
  stockLabel,
  opened,
  onClose,
}: {
  stockId: number | null;
  stockLabel: string;
  opened: boolean;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery<StockMovement[]>({
    queryKey: ["stock-movements", stockId],
    queryFn: () => stockApi.movements(stockId!),
    enabled: opened && stockId != null,
  });

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={<Text fw={600}>Movement History — {stockLabel}</Text>}
      position="right"
      size="lg"
      padding="md"
    >
      {isLoading ? (
        <Center h={200}><Loader /></Center>
      ) : !data?.length ? (
        <Center h={200}>
          <Text c="dimmed">No movements recorded yet.</Text>
        </Center>
      ) : (
        <Table striped highlightOnHover fz="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Type</Table.Th>
              <Table.Th ta="right">Qty Change</Table.Th>
              <Table.Th>Reference</Table.Th>
              <Table.Th>Notes</Table.Th>
              <Table.Th>Date</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.map((m) => {
              const qty = parseFloat(m.quantity_change);
              return (
                <Table.Tr key={m.id}>
                  <Table.Td>
                    <Badge color={MOVEMENT_COLORS[m.movement_type] ?? "gray"} variant="light" size="sm">
                      {MOVEMENT_LABELS[m.movement_type] ?? m.movement_type}
                    </Badge>
                  </Table.Td>
                  <Table.Td ta="right" fw={600} c={qty >= 0 ? "teal" : "red"}>
                    {qty >= 0 ? "+" : ""}{qty}
                  </Table.Td>
                  <Table.Td c="dimmed" fz="xs">
                    {m.reference_type ? `${m.reference_type} #${m.reference_id}` : "—"}
                  </Table.Td>
                  <Table.Td c="dimmed" fz="xs">{m.notes || "—"}</Table.Td>
                  <Table.Td c="dimmed" fz="xs">{formatDate(m.created_at)}</Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      )}
    </Drawer>
  );
}

function ExpiryBadge({ expiry_date }: { expiry_date: string | null }) {
  if (!expiry_date) return <Text c="dimmed" fz="sm">—</Text>;
  const expiry = dayjs(expiry_date);
  const daysLeft = expiry.diff(dayjs(), "day");
  if (daysLeft < 0) return <Badge color="red" variant="light" size="sm">Expired</Badge>;
  if (daysLeft <= 30) return (
    <Badge color="orange" variant="light" size="sm">
      {expiry.format("MMM D")} ({daysLeft}d)
    </Badge>
  );
  return <Badge color="teal" variant="light" size="sm">{expiry.format("MMM D, YYYY")}</Badge>;
}

export default function StockPage() {
  const [page, setPage] = useState(1);
  const [opened, { open, close }] = useDisclosure(false);
  const [movementStock, setMovementStock] = useState<{ id: number; label: string } | null>(null);
  const [movementOpened, { open: openMovements, close: closeMovements }] = useDisclosure(false);

  const { data, isLoading } = useQuery({
    queryKey: ["stock", { page }],
    queryFn: () => stockApi.list({ page }),
  });

  const totalPages = data ? Math.ceil(data.count / 20) : 1;

  return (
    <Stack>
      <PageHeader
        title="Stock"
        action={
          <Button leftSection={<IconPlus size={16} />} onClick={open}>
            Add Stock
          </Button>
        }
      />

      {isLoading ? (
        <Center h={200}><Loader /></Center>
      ) : (
        <Card shadow="sm" padding={0} radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Product</Table.Th>
                <Table.Th>Identifier</Table.Th>
                <Table.Th ta="right">Quantity</Table.Th>
                <Table.Th>Notes</Table.Th>
                <Table.Th>Expiry</Table.Th>
                <Table.Th>Added</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.results.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={6}>
                    <Center py="xl">
                      <Text c="dimmed">No stock entries yet.</Text>
                    </Center>
                  </Table.Td>
                </Table.Tr>
              ) : (
                data?.results.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td>
                      <Stack gap={0}>
                        <Text size="sm" fw={500}>{s.product_name}</Text>
                        <Badge size="xs" variant="light">{s.product_sku}</Badge>
                      </Stack>
                    </Table.Td>
                    <Table.Td><Badge variant="outline">{s.identifier}</Badge></Table.Td>
                    <Table.Td ta="right" fw={500}>{s.quantity}</Table.Td>
                    <Table.Td c="dimmed" fz="sm">{s.notes || "—"}</Table.Td>
                    <Table.Td><ExpiryBadge expiry_date={s.expiry_date} /></Table.Td>
                    <Table.Td c="dimmed" fz="sm">{formatDate(s.created_at)}</Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<IconHistory size={14} />}
                        onClick={() => {
                          setMovementStock({ id: s.id, label: `${s.product_name} / ${s.identifier}` });
                          openMovements();
                        }}
                      >
                        History
                      </Button>
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

      <StockFormModal opened={opened} onClose={close} />
      <MovementDrawer
        stockId={movementStock?.id ?? null}
        stockLabel={movementStock?.label ?? ""}
        opened={movementOpened}
        onClose={closeMovements}
      />
    </Stack>
  );
}
