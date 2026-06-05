import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Divider,
  Group,
  Loader,
  Modal,
  Progress,
  Stack,
  Table,
  Text,
  Textarea,
  ThemeIcon,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  IconAlertTriangle,
  IconBrain,
  IconCheck,
  IconInfoCircle,
  IconSearch,
  IconTruckDelivery,
  IconX,
} from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { aiWorkflowsApi, type ParsedPurchaseOrder, type ProductMatch } from "@/api/aiWorkflows";
import { purchaseOrdersApi } from "@/api/orders";
import { PageHeader } from "@/components/common/PageHeader";

const SAMPLE_INVOICE = `From: Acme Organic Farms <orders@acmefarms.com>
Date: March 15, 2025

INVOICE #INV-2025-0312

Bill To: Your Company

Items:
- Organic Rolled Oats (bulk 25kg bags) — 10 units @ $45.00/unit
- Raw Honey 500g jars — 24 units @ $8.50/unit
- Dried Blueberries 1kg — 5 units @ $22.00/unit

Payment Terms: Net 30
Delivery: 5-7 business days`;

function CreatePOModal({
  parsed,
  opened,
  onClose,
}: {
  parsed: ParsedPurchaseOrder;
  opened: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const matchedItems = parsed.product_matches.filter((m) => m.matched_product !== null);
  const [selectedItems, setSelectedItems] = useState<Set<number>>(
    new Set(matchedItems.map((_, i) => i))
  );

  const orderDate = parsed.order_date ?? new Date().toISOString().split("T")[0];

  const mutation = useMutation({
    mutationFn: async () => {
      const items = matchedItems.filter((_, i) => selectedItems.has(i));
      await Promise.all(
        items.map((item) =>
          purchaseOrdersApi.create({
            product: item.matched_product!.id,
            quantity: item.quantity,
            cost_per_unit: item.cost_per_unit ?? 0,
            order_date: orderDate,
            notes: `AI-parsed from invoice${parsed.supplier_name ? ` — ${parsed.supplier_name}` : ""}${item.notes ? `. ${item.notes}` : ""}`,
          } as any)
        )
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      notifications.show({
        title: "Draft POs Created",
        message: `${selectedItems.size} draft purchase order(s) created. Review them in Purchase Orders.`,
        color: "green",
      });
      onClose();
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Failed to create draft orders.", color: "red" });
    },
  });

  const toggleItem = (i: number) => {
    setSelectedItems((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Create Draft Purchase Orders" size="lg">
      <Stack>
        <Text size="sm" c="dimmed">
          Select the line items you want to create as draft purchase orders. Review and confirm them
          in the Purchase Orders page before stock is updated.
        </Text>

        <Stack gap="xs">
          {matchedItems.map((item, i) => (
            <Card
              key={i}
              padding="sm"
              withBorder
              style={{
                borderColor: selectedItems.has(i)
                  ? "var(--mantine-color-brand-4)"
                  : undefined,
                cursor: "pointer",
              }}
              onClick={() => toggleItem(i)}
            >
              <Group justify="space-between">
                <Group gap="xs">
                  <ThemeIcon
                    color={selectedItems.has(i) ? "brand" : "gray"}
                    variant="light"
                    size="sm"
                  >
                    {selectedItems.has(i) ? <IconCheck size={12} /> : <IconX size={12} />}
                  </ThemeIcon>
                  <div>
                    <Text size="sm" fw={500}>{item.matched_product!.name}</Text>
                    <Text size="xs" c="dimmed">{item.raw_product_name}</Text>
                  </div>
                </Group>
                <Group gap="xs">
                  <Badge variant="light">{item.quantity} units</Badge>
                  {item.cost_per_unit != null && (
                    <Badge variant="light" color="gray">${item.cost_per_unit.toFixed(2)}/unit</Badge>
                  )}
                  <Badge
                    color={item.match_confidence >= 0.8 ? "green" : item.match_confidence >= 0.5 ? "yellow" : "red"}
                    variant="light"
                    size="xs"
                  >
                    {Math.round(item.match_confidence * 100)}% match
                  </Badge>
                </Group>
              </Group>
            </Card>
          ))}
        </Stack>

        <Alert icon={<IconInfoCircle size={16} />} color="blue" variant="light">
          Each line item becomes a separate draft PO. Cost defaults to $0.00 where not detected.
          Update prices before confirming.
        </Alert>

        <Button
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={selectedItems.size === 0}
          leftSection={<IconTruckDelivery size={16} />}
          color="brand"
        >
          Create {selectedItems.size} Draft PO{selectedItems.size !== 1 ? "s" : ""}
        </Button>
      </Stack>
    </Modal>
  );
}

function MatchedProductRow({ match }: { match: ProductMatch }) {
  const isMatched = match.matched_product !== null;
  const confidencePct = Math.round(match.match_confidence * 100);
  const confidenceColor = confidencePct >= 80 ? "green" : confidencePct >= 50 ? "yellow" : "red";

  return (
    <Table.Tr>
      <Table.Td>
        <Text size="sm">{match.raw_product_name}</Text>
      </Table.Td>
      <Table.Td ta="right">{match.quantity}</Table.Td>
      <Table.Td ta="right">
        {match.cost_per_unit != null ? `$${match.cost_per_unit.toFixed(2)}` : "—"}
      </Table.Td>
      <Table.Td>
        {isMatched ? (
          <Group gap="xs">
            <ThemeIcon color="green" variant="light" size="sm">
              <IconCheck size={12} />
            </ThemeIcon>
            <div>
              <Text size="sm" fw={500}>{match.matched_product!.name}</Text>
              <Badge size="xs" variant="light">{match.matched_product!.sku}</Badge>
            </div>
          </Group>
        ) : (
          <Group gap="xs">
            <ThemeIcon color="red" variant="light" size="sm">
              <IconX size={12} />
            </ThemeIcon>
            <Text size="sm" c="dimmed">No match found</Text>
          </Group>
        )}
      </Table.Td>
      <Table.Td ta="center">
        <Group gap={4} justify="center">
          <Progress
            value={confidencePct}
            color={confidenceColor}
            size="sm"
            style={{ width: 60 }}
          />
          <Text size="xs" c="dimmed">{confidencePct}%</Text>
        </Group>
      </Table.Td>
    </Table.Tr>
  );
}

export default function AIAssistPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<ParsedPurchaseOrder | null>(null);
  const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false);

  const mutation = useMutation({
    mutationFn: () => aiWorkflowsApi.parsePurchaseOrder(text),
    onSuccess: (data) => {
      setResult(data);
    },
    onError: (err: any) => {
      const status = err?.response?.status;
      if (status === 503) {
        notifications.show({
          title: "AI Service Unavailable",
          message: "The AI service is not configured. Please contact your administrator.",
          color: "red",
        });
      } else if (status === 429) {
        notifications.show({
          title: "Rate Limited",
          message: "Too many requests. Please wait a moment and try again.",
          color: "orange",
        });
      } else {
        notifications.show({ title: "Error", message: "Failed to parse document.", color: "red" });
      }
    },
  });

  const matchedCount = result?.product_matches.filter((m) => m.matched_product !== null).length ?? 0;

  return (
    <Stack>
      <PageHeader title="AI Document Parser" />

      <Alert icon={<IconBrain size={16} />} color="brand" variant="light" title="AI-Powered Document Parsing">
        Paste any invoice, email, or vendor quote below. Claude will extract structured purchase order
        data and match it against your product catalog. You always review before creating any order.
      </Alert>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Stack>
          <Textarea
            label="Invoice / Email / Vendor Quote"
            placeholder={SAMPLE_INVOICE}
            value={text}
            onChange={(e) => setText(e.target.value)}
            minRows={8}
            autosize
          />
          <Group>
            <Button
              leftSection={<IconSearch size={16} />}
              onClick={() => mutation.mutate()}
              loading={mutation.isPending}
              disabled={!text.trim()}
              color="brand"
            >
              Parse Document
            </Button>
            <Button
              variant="subtle"
              size="sm"
              onClick={() => setText(SAMPLE_INVOICE)}
            >
              Load sample invoice
            </Button>
            {result && (
              <Button
                variant="subtle"
                color="red"
                size="sm"
                onClick={() => setResult(null)}
              >
                Clear results
              </Button>
            )}
          </Group>
        </Stack>
      </Card>

      {mutation.isPending && (
        <Center h={120}>
          <Stack align="center" gap="xs">
            <Loader size="md" />
            <Text size="sm" c="dimmed">Parsing document with Claude…</Text>
          </Stack>
        </Center>
      )}

      {result && !mutation.isPending && (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Stack>
            <Group justify="space-between">
              <Text fw={600} size="lg">Extraction Results</Text>
              <Badge
                color={result.confidence_score >= 0.8 ? "green" : result.confidence_score >= 0.5 ? "yellow" : "red"}
                variant="light"
              >
                {Math.round(result.confidence_score * 100)}% confidence
              </Badge>
            </Group>

            {(result.supplier_name || result.order_date) && (
              <Group gap="xl">
                {result.supplier_name && (
                  <div>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Supplier</Text>
                    <Text fw={500}>{result.supplier_name}</Text>
                  </div>
                )}
                {result.order_date && (
                  <div>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Order Date</Text>
                    <Text fw={500}>{result.order_date}</Text>
                  </div>
                )}
              </Group>
            )}

            {result.extraction_notes && (
              <Alert icon={<IconAlertTriangle size={16} />} color="yellow" variant="light">
                {result.extraction_notes}
              </Alert>
            )}

            <Divider />

            {result.product_matches.length > 0 ? (
              <>
                <Text fw={500}>
                  Line Items ({matchedCount} of {result.product_matches.length} matched to your catalog)
                </Text>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Document Line Item</Table.Th>
                      <Table.Th ta="right">Qty</Table.Th>
                      <Table.Th ta="right">Unit Cost</Table.Th>
                      <Table.Th>Matched Product</Table.Th>
                      <Table.Th ta="center">Confidence</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {result.product_matches.map((match, i) => (
                      <MatchedProductRow key={i} match={match} />
                    ))}
                  </Table.Tbody>
                </Table>

                {matchedCount > 0 ? (
                  <Group>
                    <Button
                      leftSection={<IconTruckDelivery size={16} />}
                      onClick={openCreate}
                      color="brand"
                    >
                      Create {matchedCount} Draft PO{matchedCount !== 1 ? "s" : ""}
                    </Button>
                    <Text size="sm" c="dimmed">
                      {result.product_matches.length - matchedCount} unmatched item{result.product_matches.length - matchedCount !== 1 ? "s" : ""} will be skipped.
                      Add those products to your catalog first.
                    </Text>
                  </Group>
                ) : (
                  <Alert icon={<IconAlertTriangle size={16} />} color="orange">
                    No products matched your catalog. Create the products first, then re-parse this document.
                  </Alert>
                )}
              </>
            ) : (
              <Alert icon={<IconInfoCircle size={16} />} color="gray">
                No line items were extracted. The document may not be a purchase order or invoice.
              </Alert>
            )}
          </Stack>
        </Card>
      )}

      {result && createOpened && (
        <CreatePOModal parsed={result} opened={createOpened} onClose={closeCreate} />
      )}
    </Stack>
  );
}
