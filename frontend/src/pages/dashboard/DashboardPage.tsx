import {
  Badge,
  Card,
  Loader,
  Center,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { BarChart } from "@mantine/charts";
import { useQuery } from "@tanstack/react-query";

import { financialsApi } from "@/api/financials";
import { formatCurrency, formatPercent } from "@/utils/formatters";

function SummaryCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={4}>
        {label}
      </Text>
      <Text size="xl" fw={700} c={color}>
        {value}
      </Text>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["financials", "summary"],
    queryFn: financialsApi.summary,
  });

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ["financials", "products"],
    queryFn: financialsApi.products,
  });

  if (summaryLoading || productsLoading) {
    return <Center h={400}><Loader /></Center>;
  }

  const chartData = (products ?? [])
    .sort((a, b) => parseFloat(b.profit) - parseFloat(a.profit))
    .slice(0, 10)
    .map((p) => ({
      product: p.product_name.length > 15 ? p.product_name.slice(0, 14) + "…" : p.product_name,
      Revenue: parseFloat(p.total_revenue),
      Cost: parseFloat(p.total_cost),
      Profit: parseFloat(p.profit),
    }));

  const profitColor = parseFloat(summary?.total_profit ?? "0") >= 0 ? "green" : "red";

  return (
    <Stack>
      <Title order={2}>Dashboard</Title>

      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }}>
        <SummaryCard label="Total Revenue" value={formatCurrency(summary?.total_revenue)} color="brand" />
        <SummaryCard label="Total Cost" value={formatCurrency(summary?.total_cost)} />
        <SummaryCard label="Total Profit" value={formatCurrency(summary?.total_profit)} color={profitColor} />
        <SummaryCard
          label="Overall Margin"
          value={summary?.overall_margin_pct != null ? formatPercent(summary.overall_margin_pct) : "—"}
          color="brand"
        />
      </SimpleGrid>

      {chartData.length > 0 && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Text fw={600} mb="md">
            Revenue vs Cost vs Profit by Product (Top 10)
          </Text>
          <BarChart
            h={280}
            data={chartData}
            dataKey="product"
            series={[
              { name: "Revenue", color: "brand.6" },
              { name: "Cost", color: "gray.5" },
              { name: "Profit", color: "green.6" },
            ]}
            tickLine="x"
          />
        </Card>
      )}

      {(products?.length ?? 0) > 0 && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Text fw={600} mb="md">
            Product Financials
          </Text>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Product</Table.Th>
                <Table.Th>SKU</Table.Th>
                <Table.Th ta="right">Cost</Table.Th>
                <Table.Th ta="right">Revenue</Table.Th>
                <Table.Th ta="right">Profit</Table.Th>
                <Table.Th ta="right">Margin</Table.Th>
                <Table.Th ta="right">Stock</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {products?.map((p) => (
                <Table.Tr key={p.product_id}>
                  <Table.Td>{p.product_name}</Table.Td>
                  <Table.Td>
                    <Badge variant="light" size="sm">
                      {p.sku}
                    </Badge>
                  </Table.Td>
                  <Table.Td ta="right">{formatCurrency(p.total_cost)}</Table.Td>
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
                  <Table.Td ta="right">{p.current_stock ?? "—"}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {(products?.length ?? 0) === 0 && (
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
