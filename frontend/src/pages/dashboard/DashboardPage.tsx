import {
  Badge,
  Button,
  Card,
  Center,
  Grid,
  Group,
  Loader,
  RingProgress,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  ThemeIcon,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { forecastingApi } from "@/api/forecasting";
import { BarChart } from "@mantine/charts";
import { useQuery } from "@tanstack/react-query";
import {
  IconAlertTriangle,
  IconArrowRight,
  IconBox,
  IconChartBar,
  IconCheck,
  IconPackage,
  IconShoppingCart,
  IconTruckDelivery,
  IconX,
} from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";

import dayjs from "dayjs";

import { financialsApi } from "@/api/financials";
import { purchaseOrdersApi, salesOrdersApi } from "@/api/orders";
import { stockApi } from "@/api/stock";
import type { Stock } from "@/types/product";
import { formatCurrency, formatPercent } from "@/utils/formatters";

function SummaryCard({
  label,
  value,
  color,
  sub,
}: {
  label: string;
  value: string;
  color?: string;
  sub?: string;
}) {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={4}>
        {label}
      </Text>
      <Text size="xl" fw={700} c={color}>
        {value}
      </Text>
      {sub && (
        <Text size="xs" c="dimmed" mt={2}>
          {sub}
        </Text>
      )}
    </Card>
  );
}

function PendingOrdersCard({
  draftPOCount,
  draftSOCount,
}: {
  draftPOCount: number;
  draftSOCount: number;
}) {
  const navigate = useNavigate();
  const total = draftPOCount + draftSOCount;

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb="md">
        Pending Actions
      </Text>
      {total === 0 ? (
        <Group gap="xs">
          <ThemeIcon color="green" variant="light" size="md">
            <IconCheck size={16} />
          </ThemeIcon>
          <Text size="sm" c="dimmed">
            All orders are up to date
          </Text>
        </Group>
      ) : (
        <Stack gap="xs">
          <UnstyledButton onClick={() => navigate("/purchase-orders")}>
            <Group justify="space-between" p="xs" style={{ borderRadius: 8, border: "1px solid var(--mantine-color-orange-3)", background: "var(--mantine-color-orange-0)" }}>
              <Group gap="xs">
                <ThemeIcon color="orange" variant="light" size="md">
                  <IconTruckDelivery size={16} />
                </ThemeIcon>
                <div>
                  <Text size="sm" fw={600}>
                    {draftPOCount} Draft Purchase{draftPOCount !== 1 ? "s" : ""}
                  </Text>
                  <Text size="xs" c="dimmed">awaiting confirmation</Text>
                </div>
              </Group>
              <IconArrowRight size={16} color="var(--mantine-color-orange-6)" />
            </Group>
          </UnstyledButton>

          <UnstyledButton onClick={() => navigate("/sales-orders")}>
            <Group justify="space-between" p="xs" style={{ borderRadius: 8, border: "1px solid var(--mantine-color-blue-3)", background: "var(--mantine-color-blue-0)" }}>
              <Group gap="xs">
                <ThemeIcon color="blue" variant="light" size="md">
                  <IconShoppingCart size={16} />
                </ThemeIcon>
                <div>
                  <Text size="sm" fw={600}>
                    {draftSOCount} Draft Sale{draftSOCount !== 1 ? "s" : ""}
                  </Text>
                  <Text size="xs" c="dimmed">awaiting confirmation</Text>
                </div>
              </Group>
              <IconArrowRight size={16} color="var(--mantine-color-blue-6)" />
            </Group>
          </UnstyledButton>
        </Stack>
      )}
    </Card>
  );
}

function InventoryHealthCard({
  outOfStock,
  lowStock,
  healthy,
  total,
}: {
  outOfStock: number;
  lowStock: number;
  healthy: number;
  total: number;
}) {
  const navigate = useNavigate();

  const segments =
    total > 0
      ? [
          { value: (healthy / total) * 100, color: "teal" },
          { value: (lowStock / total) * 100, color: "yellow" },
          { value: (outOfStock / total) * 100, color: "red" },
        ]
      : [{ value: 100, color: "gray" }];

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
      <Group justify="space-between" mb="md">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
          Inventory Health
        </Text>
        <Text size="xs" c="dimmed">{total} products</Text>
      </Group>

      {total === 0 ? (
        <Center py="xs">
          <Text size="sm" c="dimmed">No products yet</Text>
        </Center>
      ) : (
        <Group justify="space-between" align="center">
          <RingProgress
            size={90}
            thickness={10}
            sections={segments}
            label={
              <Center>
                <IconPackage size={22} color="var(--mantine-color-dimmed)" />
              </Center>
            }
          />
          <Stack gap={6} style={{ flex: 1 }}>
            <UnstyledButton onClick={() => navigate("/products")}>
              <Group gap="xs">
                <ThemeIcon color="teal" variant="light" size="sm">
                  <IconCheck size={12} />
                </ThemeIcon>
                <Text size="sm">
                  <Text span fw={700}>{healthy}</Text> healthy
                </Text>
              </Group>
            </UnstyledButton>
            <UnstyledButton onClick={() => navigate("/products")}>
              <Group gap="xs">
                <ThemeIcon color="yellow" variant="light" size="sm">
                  <IconAlertTriangle size={12} />
                </ThemeIcon>
                <Text size="sm">
                  <Text span fw={700}>{lowStock}</Text> low stock
                </Text>
              </Group>
            </UnstyledButton>
            <UnstyledButton onClick={() => navigate("/products")}>
              <Group gap="xs">
                <ThemeIcon color="red" variant="light" size="sm">
                  <IconX size={12} />
                </ThemeIcon>
                <Text size="sm">
                  <Text span fw={700}>{outOfStock}</Text> out of stock
                </Text>
              </Group>
            </UnstyledButton>
          </Stack>
        </Group>
      )}
    </Card>
  );
}

function ReorderAlertsCard({ criticalCount, lowCount }: { criticalCount: number; lowCount: number }) {
  const navigate = useNavigate();
  const total = criticalCount + lowCount;

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
      <Group justify="space-between" mb="md">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
          Reorder Alerts
        </Text>
        <IconChartBar size={16} color="var(--mantine-color-dimmed)" />
      </Group>
      {total === 0 ? (
        <Group gap="xs">
          <ThemeIcon color="green" variant="light" size="md">
            <IconCheck size={16} />
          </ThemeIcon>
          <Text size="sm" c="dimmed">All products adequately stocked</Text>
        </Group>
      ) : (
        <Stack gap="xs">
          {criticalCount > 0 && (
            <UnstyledButton onClick={() => navigate("/forecasting")}>
              <Group justify="space-between" p="xs" style={{ borderRadius: 8, border: "1px solid var(--mantine-color-orange-3)", background: "var(--mantine-color-orange-0)" }}>
                <Group gap="xs">
                  <ThemeIcon color="orange" variant="light" size="md">
                    <IconAlertTriangle size={16} />
                  </ThemeIcon>
                  <div>
                    <Text size="sm" fw={600}>{criticalCount} Critical</Text>
                    <Text size="xs" c="dimmed">≤ 3 days of stock</Text>
                  </div>
                </Group>
                <IconArrowRight size={16} color="var(--mantine-color-orange-6)" />
              </Group>
            </UnstyledButton>
          )}
          {lowCount > 0 && (
            <UnstyledButton onClick={() => navigate("/forecasting")}>
              <Group justify="space-between" p="xs" style={{ borderRadius: 8, border: "1px solid var(--mantine-color-yellow-3)", background: "var(--mantine-color-yellow-0)" }}>
                <Group gap="xs">
                  <ThemeIcon color="yellow" variant="light" size="md">
                    <IconAlertTriangle size={16} />
                  </ThemeIcon>
                  <div>
                    <Text size="sm" fw={600}>{lowCount} Low Stock</Text>
                    <Text size="xs" c="dimmed">below reorder point</Text>
                  </div>
                </Group>
                <IconArrowRight size={16} color="var(--mantine-color-yellow-6)" />
              </Group>
            </UnstyledButton>
          )}
        </Stack>
      )}
    </Card>
  );
}

function ExpiringLotsCard({ lots }: { lots: Stock[] }) {
  const navigate = useNavigate();

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder h="100%">
      <Group justify="space-between" mb="md">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
          Expiring Soon
        </Text>
        <Text size="xs" c="dimmed">next 30 days</Text>
      </Group>

      {lots.length === 0 ? (
        <Group gap="xs">
          <ThemeIcon color="green" variant="light" size="md">
            <IconCheck size={16} />
          </ThemeIcon>
          <Text size="sm" c="dimmed">No lots expiring soon</Text>
        </Group>
      ) : (
        <Stack gap="xs">
          {lots.slice(0, 4).map((lot) => {
            const daysLeft = dayjs(lot.expiry_date!).diff(dayjs(), "day");
            const color = daysLeft < 0 ? "red" : daysLeft <= 7 ? "red" : "orange";
            return (
              <UnstyledButton key={lot.id} onClick={() => navigate("/stock")}>
                <Group
                  justify="space-between"
                  p="xs"
                  style={{
                    borderRadius: 8,
                    border: `1px solid var(--mantine-color-${color}-3)`,
                    background: `var(--mantine-color-${color}-0)`,
                  }}
                >
                  <div>
                    <Text size="sm" fw={600}>{lot.product_name}</Text>
                    <Text size="xs" c="dimmed">Lot {lot.identifier} · {lot.quantity}</Text>
                  </div>
                  <Badge color={color} variant="light" size="xs">
                    {daysLeft < 0 ? "Expired" : `${daysLeft}d`}
                  </Badge>
                </Group>
              </UnstyledButton>
            );
          })}
          {lots.length > 4 && (
            <Text size="xs" c="dimmed" ta="center">+{lots.length - 4} more</Text>
          )}
        </Stack>
      )}
    </Card>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["financials", "summary"],
    queryFn: financialsApi.summary,
  });

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ["financials", "products"],
    queryFn: financialsApi.products,
  });

  const { data: draftPOs } = useQuery({
    queryKey: ["purchase-orders", { status: "draft" }],
    queryFn: () => purchaseOrdersApi.list({ status: "draft" }),
  });

  const { data: draftSOs } = useQuery({
    queryKey: ["sales-orders", { status: "draft" }],
    queryFn: () => salesOrdersApi.list({ status: "draft" }),
  });

  const { data: expiringLots } = useQuery({
    queryKey: ["stock", "expiring_soon"],
    queryFn: () => stockApi.expiringSoon(30),
  });

  const { data: reorderData } = useQuery({
    queryKey: ["forecasting", "reorder-recommendations"],
    queryFn: forecastingApi.reorderRecommendations,
  });

  if (summaryLoading || productsLoading) {
    return <Center h={400}><Loader /></Center>;
  }

  const productList = products ?? [];
  const totalProducts = productList.length;

  const outOfStock = productList.filter((p) => parseFloat(p.current_stock ?? "0") === 0).length;
  const lowStock = productList.filter((p) => {
    const stock = parseFloat(p.current_stock ?? "0");
    const threshold = p.min_stock_quantity > 0 ? p.min_stock_quantity : 5;
    return stock > 0 && stock < threshold;
  }).length;
  const healthy = totalProducts - outOfStock - lowStock;

  const revenueChartData = productList
    .sort((a, b) => parseFloat(b.profit) - parseFloat(a.profit))
    .slice(0, 10)
    .map((p) => ({
      product: p.product_name.length > 14 ? p.product_name.slice(0, 13) + "…" : p.product_name,
      Revenue: parseFloat(p.total_revenue),
      Cost: parseFloat(p.cogs),
      Profit: parseFloat(p.profit),
    }));

  const marginChartData = [...productList]
    .filter((p) => p.margin_pct != null)
    .sort((a, b) => parseFloat(b.margin_pct!) - parseFloat(a.margin_pct!))
    .slice(0, 10)
    .map((p) => ({
      product: p.product_name.length > 14 ? p.product_name.slice(0, 13) + "…" : p.product_name,
      "Margin %": parseFloat(p.margin_pct!),
    }));

  const profitColor = parseFloat(summary?.total_profit ?? "0") >= 0 ? "green" : "red";
  const draftPOCount = draftPOs?.count ?? 0;
  const draftSOCount = draftSOs?.count ?? 0;
  const reorderList = reorderData ?? [];
  const criticalCount = reorderList.filter((r) => r.status === "CRITICAL" || r.status === "OUT_OF_STOCK").length;
  const lowCount = reorderList.filter((r) => r.status === "LOW").length;

  return (
    <Stack>
      <Group justify="space-between" align="center">
        <Title order={2}>Dashboard</Title>
        <Group gap="xs">
          <Button
            leftSection={<IconBox size={15} />}
            variant="light"
            size="xs"
            onClick={() => navigate("/products")}
          >
            Products
          </Button>
          <Button
            leftSection={<IconTruckDelivery size={15} />}
            variant="light"
            size="xs"
            onClick={() => navigate("/purchase-orders")}
          >
            Purchase Orders
          </Button>
          <Button
            leftSection={<IconShoppingCart size={15} />}
            variant="light"
            size="xs"
            onClick={() => navigate("/sales-orders")}
          >
            Sales Orders
          </Button>
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, md: 5 }}>
        <SummaryCard label="Total Revenue" value={formatCurrency(summary?.total_revenue)} color="brand" />
        <SummaryCard label="COGS" value={formatCurrency(summary?.total_cogs)} />
        <SummaryCard label="Total Profit" value={formatCurrency(summary?.total_profit)} color={profitColor} />
        <SummaryCard
          label="Overall Margin"
          value={summary?.overall_margin_pct != null ? formatPercent(summary.overall_margin_pct) : "—"}
          color="brand"
        />
        <SummaryCard
          label="Inventory Value"
          value={formatCurrency(summary?.inventory_value)}
          sub="capital in stock"
        />
      </SimpleGrid>

      <Grid>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <PendingOrdersCard draftPOCount={draftPOCount} draftSOCount={draftSOCount} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InventoryHealthCard
            outOfStock={outOfStock}
            lowStock={lowStock}
            healthy={healthy}
            total={totalProducts}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <ReorderAlertsCard criticalCount={criticalCount} lowCount={lowCount} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <ExpiringLotsCard lots={expiringLots ?? []} />
        </Grid.Col>
      </Grid>

      {productList.length > 0 && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Tabs defaultValue="financials">
            <Tabs.List mb="md">
              <Tabs.Tab value="financials">Revenue vs Cost vs Profit</Tabs.Tab>
              <Tabs.Tab value="margin">Margin % by Product</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="financials">
              <BarChart
                h={280}
                data={revenueChartData}
                dataKey="product"
                series={[
                  { name: "Revenue", color: "brand.6" },
                  { name: "Cost", color: "gray.5" },
                  { name: "Profit", color: "green.6" },
                ]}
                tickLine="x"
              />
            </Tabs.Panel>

            <Tabs.Panel value="margin">
              {marginChartData.length > 0 ? (
                <BarChart
                  h={280}
                  data={marginChartData}
                  dataKey="product"
                  series={[{ name: "Margin %", color: "brand.6" }]}
                  tickLine="x"
                />
              ) : (
                <Center h={280}>
                  <Text c="dimmed" size="sm">No margin data yet. Confirm purchase and sales orders to see margin.</Text>
                </Center>
              )}
            </Tabs.Panel>
          </Tabs>
        </Card>
      )}

      {productList.length > 0 && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Text fw={600} mb="md">
            Product Financials
          </Text>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Product</Table.Th>
                <Table.Th>SKU</Table.Th>
                <Table.Th ta="right">COGS</Table.Th>
                <Table.Th ta="right">Revenue</Table.Th>
                <Table.Th ta="right">Profit</Table.Th>
                <Table.Th ta="right">Margin</Table.Th>
                <Table.Th ta="right">Stock</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {productList.map((p) => {
                const stock = parseFloat(p.current_stock ?? "0");
                const threshold = p.min_stock_quantity > 0 ? p.min_stock_quantity : 5;
                const stockColor = stock === 0 ? "red" : stock < threshold ? "yellow" : "teal";
                const stockLabel = stock === 0 ? "Out of stock" : stock < threshold ? "Low" : "OK";
                return (
                  <Table.Tr key={p.product_id}>
                    <Table.Td>{p.product_name}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" size="sm">
                        {p.sku}
                      </Badge>
                    </Table.Td>
                    <Table.Td ta="right">{formatCurrency(p.cogs)}</Table.Td>
                    <Table.Td ta="right">{formatCurrency(p.total_revenue)}</Table.Td>
                    <Table.Td ta="right" c={parseFloat(p.profit) >= 0 ? "green" : "red"}>
                      {formatCurrency(p.profit)}
                    </Table.Td>
                    <Table.Td ta="right">
                      {p.margin_pct != null ? (
                        <Badge color={parseFloat(p.margin_pct) >= 0 ? "green" : "red"} variant="light">
                          {formatPercent(p.margin_pct)}
                        </Badge>
                      ) : "—"}
                    </Table.Td>
                    <Table.Td ta="right">
                      <Badge color={stockColor} variant="light" size="sm">
                        {p.current_stock ?? "0"} · {stockLabel}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {productList.length === 0 && (
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Center>
            <Stack align="center" gap="xs">
              <Text c="dimmed" size="lg">No data yet</Text>
              <Text c="dimmed" size="sm">Create products and add orders to see financial metrics here.</Text>
            </Stack>
          </Center>
        </Card>
      )}
    </Stack>
  );
}
