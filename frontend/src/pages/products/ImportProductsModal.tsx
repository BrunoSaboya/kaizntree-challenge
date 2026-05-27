import {
  Alert,
  Badge,
  Button,
  FileButton,
  Group,
  Loader,
  Modal,
  NumberInput,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconCheck, IconDownload, IconUpload, IconX } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { z } from "zod";

import { productsApi } from "@/api/products";
import { UNIT_TYPE_LABELS } from "@/types/product";
import { mapCsvToProducts, parseCsvText } from "@/utils/csvParser";

const importSchema = z.object({
  name: z.string().min(1, "Name is required"),
  sku: z.string().min(1, "SKU is required"),
  unit_type: z.enum(["kg", "g", "l", "ml", "count"]).default("count"),
  description: z.string().optional(),
  min_stock_quantity: z.coerce.number().int().min(0).default(0),
});

type FormValues = z.infer<typeof importSchema>;

type RowStatus = "pending" | "submitting" | "success" | "error";

interface ImportRow {
  _id: string;
  values: Partial<FormValues>;
  clientErrors: Record<string, string>;
  status: RowStatus;
  serverError?: string;
}

function validateRow(values: Partial<FormValues>): Record<string, string> {
  const result = importSchema.safeParse(values);
  if (result.success) return {};
  const errors: Record<string, string> = {};
  result.error.issues.forEach((issue) => {
    const key = issue.path[0] as string;
    if (!errors[key]) errors[key] = issue.message;
  });
  return errors;
}

function extractServerError(err: unknown): string {
  const data = (err as any)?.response?.data;
  if (!data) return "Network error";
  return (
    data?.sku?.[0] ??
    data?.name?.[0] ??
    data?.unit_type?.[0] ??
    data?.min_stock_quantity?.[0] ??
    data?.description?.[0] ??
    data?.detail ??
    data?.non_field_errors?.[0] ??
    "Import failed"
  );
}

const SAMPLE_CSV = `name,sku,unit_type,description,min_stock_quantity
Oat Milk 1L,OAT-001,l,Organic oat milk,12
Almonds,ALM-200,kg,,5
Packaging Bags,PKG-500,count,"Small poly bags, 100-pack",0
`;

interface Props {
  opened: boolean;
  onClose: () => void;
}

export function ImportProductsModal({ opened, onClose }: Props) {
  const queryClient = useQueryClient();
  const resetRef = useRef<() => void>(null);

  const [step, setStep] = useState<"upload" | "review" | "done">("upload");
  const [fileName, setFileName] = useState<string>("");
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [unknownHeaders, setUnknownHeaders] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [parseError, setParseError] = useState<string>("");

  function handleClose() {
    setStep("upload");
    setFileName("");
    setRows([]);
    setUnknownHeaders([]);
    setIsSubmitting(false);
    setParseError("");
    resetRef.current?.();
    onClose();
  }

  function handleFile(file: File | null) {
    if (!file) return;
    setParseError("");
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const raw = parseCsvText(text);
      if (raw.length < 2) {
        setParseError("The CSV must have a header row and at least one data row.");
        return;
      }
      const { mapped, unknownHeaders: unknown } = mapCsvToProducts(raw);
      if (mapped.length === 0) {
        setParseError("No valid data rows found. Check that your file has a header row.");
        return;
      }
      setUnknownHeaders(unknown);
      const importRows: ImportRow[] = mapped.map((raw) => {
        const values: Partial<FormValues> = {
          name: raw.name,
          sku: raw.sku,
          unit_type: (raw.unit_type as FormValues["unit_type"]) || "count",
          description: raw.description,
          min_stock_quantity: raw.min_stock_quantity === "" ? 0 : Number(raw.min_stock_quantity),
        };
        return {
          _id: crypto.randomUUID(),
          values,
          clientErrors: validateRow(values),
          status: "pending",
        };
      });
      setRows(importRows);
      setStep("review");
    };
    reader.readAsText(file);
  }

  function updateRow(id: string, field: keyof FormValues, value: unknown) {
    setRows((prev) =>
      prev.map((row) => {
        if (row._id !== id) return row;
        const values = { ...row.values, [field]: value };
        return { ...row, values, clientErrors: validateRow(values) };
      })
    );
  }

  function deleteRow(id: string) {
    setRows((prev) => prev.filter((r) => r._id !== id));
  }

  async function handleImport() {
    setIsSubmitting(true);
    let successCount = 0;
    let errorCount = 0;

    for (const row of rows) {
      setRows((prev) =>
        prev.map((r) => (r._id === row._id ? { ...r, status: "submitting" } : r))
      );
      try {
        await productsApi.create(row.values as FormValues);
        setRows((prev) =>
          prev.map((r) => (r._id === row._id ? { ...r, status: "success" } : r))
        );
        successCount++;
      } catch (err) {
        const serverError = extractServerError(err);
        setRows((prev) =>
          prev.map((r) => (r._id === row._id ? { ...r, status: "error", serverError } : r))
        );
        errorCount++;
      }
    }

    queryClient.invalidateQueries({ queryKey: ["products"] });
    setIsSubmitting(false);
    setStep("done");

    if (errorCount === 0) {
      notifications.show({
        title: "Import complete",
        message: `${successCount} product${successCount !== 1 ? "s" : ""} imported successfully.`,
        color: "green",
      });
    }
  }

  function downloadSample() {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample_products.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const validRowCount = rows.filter((r) => Object.keys(r.clientErrors).length === 0).length;
  const errorRowCount = rows.length - validRowCount;
  const successCount = rows.filter((r) => r.status === "success").length;
  const failedCount = rows.filter((r) => r.status === "error").length;
  const hasClientErrors = errorRowCount > 0;

  function renderStatusBadge(row: ImportRow) {
    if (row.status === "submitting") return <Loader size="xs" />;
    if (row.status === "success") return <Badge color="green" size="sm">Created</Badge>;
    if (row.status === "error") return (
      <Stack gap={2}>
        <Badge color="red" size="sm">Failed</Badge>
        <Text fz="xs" c="red">{row.serverError}</Text>
      </Stack>
    );
    if (Object.keys(row.clientErrors).length > 0) return <Badge color="orange" size="sm">Has errors</Badge>;
    return <Badge color="gray" variant="outline" size="sm">Pending</Badge>;
  }

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Import Products from CSV"
      size="xl"
      scrollAreaComponent={ScrollArea.Autosize}
    >
      <Stack>
        {step === "upload" && (
          <>
            <Text size="sm" c="dimmed">
              Upload a CSV file with a header row. Column names are matched case-insensitively.
              Supported columns: <b>name</b>, <b>sku</b>, <b>unit_type</b>, <b>description</b>, <b>min_stock_quantity</b>.
            </Text>

            <Alert color="blue" variant="light">
              <Text size="sm" fw={500} mb={4}>Expected format:</Text>
              <Text size="xs" ff="monospace" style={{ whiteSpace: "pre" }}>
                {`name,sku,unit_type,description,min_stock_quantity\nOat Milk 1L,OAT-001,l,Organic oat milk,12\nAlmonds,ALM-200,kg,,5`}
              </Text>
              <Text size="xs" c="dimmed" mt={6}>
                • unit_type: kg / g / l / ml / count (defaults to count if blank)<br />
                • description and min_stock_quantity are optional<br />
                • Values containing commas must be wrapped in double quotes
              </Text>
            </Alert>

            {parseError && (
              <Alert color="red" icon={<IconAlertTriangle size={16} />}>
                {parseError}
              </Alert>
            )}

            <Group>
              <FileButton resetRef={resetRef} onChange={handleFile} accept=".csv,text/csv">
                {(props) => (
                  <Button {...props} leftSection={<IconUpload size={16} />}>
                    {fileName ? `Re-upload (${fileName})` : "Upload CSV"}
                  </Button>
                )}
              </FileButton>
              <Button variant="default" leftSection={<IconDownload size={16} />} onClick={downloadSample}>
                Download sample
              </Button>
            </Group>
          </>
        )}

        {(step === "review" || step === "done") && (
          <>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                {rows.length} rows · {validRowCount} valid
                {errorRowCount > 0 && ` · ${errorRowCount} with errors`}
              </Text>
              {step === "done" && (
                <Badge color={failedCount === 0 ? "green" : successCount === 0 ? "red" : "yellow"} size="lg">
                  {successCount}/{rows.length} imported
                </Badge>
              )}
            </Group>

            {unknownHeaders.length > 0 && (
              <Alert color="yellow" icon={<IconAlertTriangle size={16} />}>
                Unknown columns ignored: {unknownHeaders.join(", ")}
              </Alert>
            )}

            {step === "done" && failedCount > 0 && successCount > 0 && (
              <Alert color="yellow" icon={<IconAlertTriangle size={16} />}>
                {failedCount} row{failedCount !== 1 ? "s" : ""} failed. Review the errors below.
              </Alert>
            )}
            {step === "done" && successCount === 0 && (
              <Alert color="red" icon={<IconX size={16} />}>
                All rows failed to import. Check the errors below and try again.
              </Alert>
            )}
            {step === "done" && failedCount === 0 && (
              <Alert color="green" icon={<IconCheck size={16} />}>
                All {successCount} products imported successfully.
              </Alert>
            )}

            <ScrollArea>
              <Table striped highlightOnHover withColumnBorders style={{ minWidth: 900 }}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th style={{ minWidth: 160 }}>Name *</Table.Th>
                    <Table.Th style={{ minWidth: 120 }}>SKU *</Table.Th>
                    <Table.Th style={{ minWidth: 120 }}>Unit Type</Table.Th>
                    <Table.Th style={{ minWidth: 200 }}>Description</Table.Th>
                    <Table.Th style={{ minWidth: 100 }}>Min Stock</Table.Th>
                    <Table.Th style={{ minWidth: 90 }}>Status</Table.Th>
                    {step === "review" && <Table.Th style={{ minWidth: 50 }}></Table.Th>}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((row) => (
                    <Table.Tr
                      key={row._id}
                      style={
                        Object.keys(row.clientErrors).length > 0 && row.status === "pending"
                          ? { borderLeft: "3px solid var(--mantine-color-red-6)" }
                          : undefined
                      }
                    >
                      <Table.Td>
                        <TextInput
                          size="xs"
                          value={row.values.name ?? ""}
                          onChange={(e) => updateRow(row._id, "name", e.target.value)}
                          error={row.clientErrors.name}
                          disabled={row.status !== "pending"}
                        />
                      </Table.Td>
                      <Table.Td>
                        <TextInput
                          size="xs"
                          value={row.values.sku ?? ""}
                          onChange={(e) => updateRow(row._id, "sku", e.target.value)}
                          error={row.clientErrors.sku}
                          disabled={row.status !== "pending"}
                        />
                      </Table.Td>
                      <Table.Td>
                        <Select
                          size="xs"
                          data={Object.entries(UNIT_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
                          value={row.values.unit_type ?? "count"}
                          onChange={(v) => updateRow(row._id, "unit_type", v ?? "count")}
                          error={row.clientErrors.unit_type}
                          disabled={row.status !== "pending"}
                        />
                      </Table.Td>
                      <Table.Td>
                        <TextInput
                          size="xs"
                          value={row.values.description ?? ""}
                          onChange={(e) => updateRow(row._id, "description", e.target.value)}
                          disabled={row.status !== "pending"}
                        />
                      </Table.Td>
                      <Table.Td>
                        <NumberInput
                          size="xs"
                          value={row.values.min_stock_quantity ?? 0}
                          onChange={(v) => updateRow(row._id, "min_stock_quantity", v)}
                          min={0}
                          error={row.clientErrors.min_stock_quantity}
                          disabled={row.status !== "pending"}
                        />
                      </Table.Td>
                      <Table.Td>{renderStatusBadge(row)}</Table.Td>
                      {step === "review" && (
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="subtle"
                            color="red"
                            px={6}
                            onClick={() => deleteRow(row._id)}
                          >
                            ✕
                          </Button>
                        </Table.Td>
                      )}
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </>
        )}

        <Group justify="flex-end">
          {step === "upload" && (
            <Button variant="default" onClick={handleClose}>Cancel</Button>
          )}
          {step === "review" && (
            <>
              <Button
                variant="default"
                onClick={() => { setStep("upload"); setRows([]); setFileName(""); resetRef.current?.(); }}
              >
                Back
              </Button>
              <Button
                leftSection={<IconUpload size={16} />}
                onClick={handleImport}
                disabled={hasClientErrors || rows.length === 0 || isSubmitting}
                loading={isSubmitting}
              >
                Import {rows.length} product{rows.length !== 1 ? "s" : ""}
              </Button>
            </>
          )}
          {step === "done" && (
            <Button onClick={handleClose}>Close</Button>
          )}
        </Group>
      </Stack>
    </Modal>
  );
}
