import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertTriangle,
  IconInfoCircle,
  IconRefresh,
  IconTruckDelivery,
} from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { forecastingApi } from "@/api/forecasting";
import { purchaseOrdersApi } from "@/api/orders";
import { productsApi } from "@/api/products";
import { PageHeader } from "@/components/common/PageHeader";
import {
  REORDER_STATUS_COLORS,
  REORDER_STATUS_LABELS,
  type ReorderRecommendation,
} from "@/types/forecasting";

function CreateDraftPOModal({
  rec,
  opened,
  onClose,
}: {
  rec: ReorderRecommendation;
  opened: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [identifier, setIdentifier] = useState(`PO-${rec.sku}-${new Date().toISOString().split("T")[0]}`);

  const { data: products } = useQuery({
    queryKey: ["products", { sku: rec.sku }],
    queryFn: () => productsApi.list({ search: rec.sku }),
    enabled: opened,
  });

  const product = products?.results.find((p) => p.sku === rec.sku);

  const mutation = useMutation({
    mutationFn: () =>
      purchaseOrdersApi.create({
        product: product?.id ?? rec.product_id,
        quantity: rec.recommended_reorder_qty,
        cost_per_unit: 0,
        order_date: new Date().toISOString().split("T")[0],
        notes: `Auto-generated from reorder recommendation. Reorder point: ${rec.reorder_point.toFixed(1)} ${rec.unit_type}.`,
      } as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      notifications.show({
        title: "Draft PO Created",
        message: `Draft purchase order for ${rec.product_name} created. Go to Purchase Orders to confirm.`,
        color: "green",
      });
      onClose();
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Failed to create draft PO.", color: "red" });
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title="Create Draft Purchase Order">
      <Stack>
        <Text size="sm" c="dimmed">
          Create a draft purchase order for <strong>{rec.product_name}</strong> based on the reorder recommendation.
          You can review and edit it before confirming.
        </Text>
        <Group grow>
          <div>
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">Recommended Qty</Text>
            <Text fw={600}>{rec.recommended_reorder_qty.toFixed(1)} {rec.unit_type}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">Lead Time</Text>
            <Text fw={600}>{rec.lead_time_days} days</Text>
          </div>
        </Group>
        <TextInput
          label="PO Reference"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          description="Used as notes reference for this order"
        />
        <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
          Cost per unit defaults to $0.00. Update it in the Purchase Orders page before confirming.
        </Alert>
        <Button
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          color="brand"
          leftSection={<IconTruckDelivery size={16} />}
        >
          Create Draft PO
        </Button>
      </Stack>
    </Modal>
  );
}

export default function ForecastingPage() {
  const [selectedRec, setSelectedRec] = useState<ReorderRecommendation | null>(null);
  const [poModalOpened, { open: openPOModal, close: closePOModal }] = useDisclosure(false);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["forecasting", "reorder-recommendations"],
    queryFn: forecastingApi.reorderRecommendations,
  });

  const recommendations = data ?? [];
  const alertCount = recommendations.filter((r) => r.status === "CRITICAL" || r.status === "LOW" || r.status === "OUT_OF_STOCK").length;

  return (
    <Stack>
      <PageHeader
        title="Demand Forecasting"
        action={
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            onClick={() => refetch()}
            loading={isFetching}
          >
            Refresh
          </Button>
        }
      />

      {alertCount > 0 && (
        <Alert
          icon={<IconAlertTriangle size={16} />}
          color="orange"
          variant="light"
          title={`${alertCount} product${alertCount !== 1 ? "s" : ""} need${alertCount === 1 ? "s" : ""} attention`}
        >
          Review the products below and create draft purchase orders where needed.
        </Alert>
      )}

      {isLoading ? (
        <Center h={200}>
          <Loader />
        </Center>
      ) : (
        <Card shadow="sm" padding={0} radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Product</Table.Th>
                <Table.Th ta="right">Current Stock</Table.Th>
                <Table.Th ta="right">Daily Usage</Table.Th>
                <Table.Th ta="right">Days Remaining</Table.Th>
                <Table.Th ta="right">Reorder Point</Table.Th>
                <Table.Th ta="right">Suggested Order</Table.Th>
                <Table.Th ta="center">Status</Table.Th>
                <Table.Th ta="center">Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {recommendations.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={8}>
                    <Center py="xl">
                      <Text c="dimmed">No products found. Create products and record sales to see forecasting data.</Text>
                    </Center>
                  </Table.Td>
                </Table.Tr>
              ) : (
                recommendations.map((rec) => (
                  <Table.Tr key={rec.product_id}>
                    <Table.Td>
                      <Stack gap={0}>
                        <Text size="sm" fw={500}>{rec.product_name}</Text>
                        <Badge size="xs" variant="light">{rec.sku}</Badge>
                      </Stack>
                    </Table.Td>
                    <Table.Td ta="right">
                      {rec.current_stock.toFixed(1)} {rec.unit_type}
                    </Table.Td>
                    <Table.Td ta="right">
                      {rec.avg_daily_consumption > 0
                        ? `${rec.avg_daily_consumption.toFixed(2)}/day`
                        : <Text size="sm" c="dimmed">—</Text>}
                    </Table.Td>
                    <Table.Td ta="right">
                      {rec.days_of_stock_remaining != null
                        ? <Text fw={rec.days_of_stock_remaining <= 7 ? 700 : undefined}>{rec.days_of_stock_remaining}d</Text>
                        : <Text size="sm" c="dimmed">∞</Text>}
                    </Table.Td>
                    <Table.Td ta="right">
                      {rec.reorder_point > 0
                        ? `${rec.reorder_point.toFixed(1)} ${rec.unit_type}`
                        : <Text size="sm" c="dimmed">—</Text>}
                    </Table.Td>
                    <Table.Td ta="right" fw={500}>
                      {rec.recommended_reorder_qty.toFixed(1)} {rec.unit_type}
                    </Table.Td>
                    <Table.Td ta="center">
                      <Badge
                        color={REORDER_STATUS_COLORS[rec.status]}
                        variant={rec.status === "OK" ? "outline" : "light"}
                      >
                        {REORDER_STATUS_LABELS[rec.status]}
                      </Badge>
                    </Table.Td>
                    <Table.Td ta="center">
                      {rec.status !== "OK" && (
                        <Button
                          size="xs"
                          variant="light"
                          color="brand"
                          leftSection={<IconTruckDelivery size={14} />}
                          onClick={() => {
                            setSelectedRec(rec);
                            openPOModal();
                          }}
                        >
                          Draft PO
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {selectedRec && (
        <CreateDraftPOModal
          rec={selectedRec}
          opened={poModalOpened}
          onClose={() => {
            closePOModal();
            setSelectedRec(null);
          }}
        />
      )}
    </Stack>
  );
}
