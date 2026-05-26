import {
  Badge,
  Button,
  Card,
  Center,
  Grid,
  Group,
  Loader,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { productsApi } from "@/api/products";
import { formatCurrency, formatDate, formatPercent, formatQuantity } from "@/utils/formatters";
import { ORDER_STATUS_COLORS, ORDER_STATUS_LABELS, type PurchaseOrder, type SalesOrder } from "@/types/orders";
import { purchaseOrdersApi, salesOrdersApi } from "@/api/orders";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const productId = parseInt(id!, 10);

  const { data: product, isLoading } = useQuery({
    queryKey: ["products", productId],
    queryFn: () => productsApi.get(productId),
  });

  const { data: stock } = useQuery({
    queryKey: ["products", productId, "stock"],
    queryFn: () => productsApi.getStock(productId),
    enabled: !!productId,
  });

  const { data: financials } = useQuery({
    queryKey: ["products", productId, "financials"],
    queryFn: () => productsApi.getFinancials(productId),
    enabled: !!productId,
  });

  const { data: pos } = useQuery({
    queryKey: ["purchase-orders", { product: productId }],
    queryFn: () => purchaseOrdersApi.list({ product: productId }),
    enabled: !!productId,
  });

  const { data: sos } = useQuery({
    queryKey: ["sales-orders", { product: productId }],
    queryFn: () => salesOrdersApi.list({ product: productId }),
    enabled: !!productId,
  });

  if (isLoading) return <Center h={300}><Loader /></Center>;
  if (!product) return <Text>Product not found.</Text>;

  return (
    <Stack>
      <Group>
        <Button component={Link} to="/products" variant="subtle" leftSection={<IconArrowLeft size={16} />}>
          Back to Products
        </Button>
      </Group>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 8 }}>
            <Title order={3}>{product.name}</Title>
            <Text c="dimmed" mt={4}>{product.description || "No description."}</Text>
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <Stack gap={4}>
              <Group gap="xs">
                <Text size="sm" c="dimmed">SKU:</Text>
                <Badge variant="light">{product.sku}</Badge>
              </Group>
              <Group gap="xs">
                <Text size="sm" c="dimmed">Unit:</Text>
                <Text size="sm">{product.unit_type}</Text>
              </Group>
              <Group gap="xs">
                <Text size="sm" c="dimmed">Total Stock:</Text>
                <Text size="sm" fw={600} c="green">
                  {formatQuantity(product.total_stock, product.unit_type)}
                </Text>
              </Group>
            </Stack>
          </Grid.Col>
        </Grid>
      </Card>

      {financials && (
        <Grid>
          {[
            { label: "Total Cost", value: formatCurrency(financials.total_cost) },
            { label: "Total Revenue", value: formatCurrency(financials.total_revenue) },
            { label: "Profit", value: formatCurrency(financials.profit), color: parseFloat(financials.profit) >= 0 ? "green" : "red" },
            { label: "Margin", value: financials.margin_pct != null ? formatPercent(financials.margin_pct) : "—", color: "violet" },
          ].map(({ label, value, color }) => (
            <Grid.Col key={label} span={{ base: 6, sm: 3 }}>
              <Card shadow="xs" padding="md" radius="md" withBorder>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{label}</Text>
                <Text size="lg" fw={700} c={color}>{value}</Text>
              </Card>
            </Grid.Col>
          ))}
        </Grid>
      )}

      <Tabs defaultValue="stock">
        <Tabs.List>
          <Tabs.Tab value="stock">Stock ({stock?.length ?? 0})</Tabs.Tab>
          <Tabs.Tab value="purchase-orders">Purchase Orders ({pos?.count ?? 0})</Tabs.Tab>
          <Tabs.Tab value="sales-orders">Sales Orders ({sos?.count ?? 0})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="stock" pt="md">
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Identifier</Table.Th>
                <Table.Th ta="right">Quantity</Table.Th>
                <Table.Th>Notes</Table.Th>
                <Table.Th>Added</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {!stock?.length ? (
                <Table.Tr><Table.Td colSpan={4}><Center py="md"><Text c="dimmed">No stock entries.</Text></Center></Table.Td></Table.Tr>
              ) : stock.map((s) => (
                <Table.Tr key={s.id}>
                  <Table.Td><Badge variant="outline">{s.identifier}</Badge></Table.Td>
                  <Table.Td ta="right">{formatQuantity(s.quantity)}</Table.Td>
                  <Table.Td c="dimmed">{s.notes || "—"}</Table.Td>
                  <Table.Td c="dimmed">{formatDate(s.created_at)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Tabs.Panel>

        <Tabs.Panel value="purchase-orders" pt="md">
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th ta="right">Qty</Table.Th>
                <Table.Th ta="right">Cost/Unit</Table.Th>
                <Table.Th ta="right">Total</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {!pos?.results.length ? (
                <Table.Tr><Table.Td colSpan={5}><Center py="md"><Text c="dimmed">No purchase orders.</Text></Center></Table.Td></Table.Tr>
              ) : pos.results.map((po: PurchaseOrder) => (
                <Table.Tr key={po.id}>
                  <Table.Td>{formatDate(po.order_date)}</Table.Td>
                  <Table.Td ta="right">{po.quantity}</Table.Td>
                  <Table.Td ta="right">{formatCurrency(po.cost_per_unit)}</Table.Td>
                  <Table.Td ta="right">{formatCurrency(po.total_cost)}</Table.Td>
                  <Table.Td>
                    <Badge color={ORDER_STATUS_COLORS[po.status]} variant="light">
                      {ORDER_STATUS_LABELS[po.status]}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Tabs.Panel>

        <Tabs.Panel value="sales-orders" pt="md">
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th ta="right">Qty</Table.Th>
                <Table.Th ta="right">Price/Unit</Table.Th>
                <Table.Th ta="right">Revenue</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {!sos?.results.length ? (
                <Table.Tr><Table.Td colSpan={5}><Center py="md"><Text c="dimmed">No sales orders.</Text></Center></Table.Td></Table.Tr>
              ) : sos.results.map((so: SalesOrder) => (
                <Table.Tr key={so.id}>
                  <Table.Td>{formatDate(so.order_date)}</Table.Td>
                  <Table.Td ta="right">{so.quantity}</Table.Td>
                  <Table.Td ta="right">{formatCurrency(so.price_per_unit)}</Table.Td>
                  <Table.Td ta="right">{formatCurrency(so.total_revenue)}</Table.Td>
                  <Table.Td>
                    <Badge color={ORDER_STATUS_COLORS[so.status]} variant="light">
                      {ORDER_STATUS_LABELS[so.status]}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
