import {
  ActionIcon,
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
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconEdit, IconEye, IconPlus, IconSearch, IconTrash } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { zodResolver } from "mantine-form-zod-resolver";
import { Link } from "react-router-dom";
import { z } from "zod";

import { productsApi } from "@/api/products";
import { PageHeader } from "@/components/common/PageHeader";
import type { Product } from "@/types/product";
import { UNIT_TYPE_LABELS } from "@/types/product";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  sku: z.string().min(1, "SKU is required"),
  unit_type: z.enum(["kg", "g", "l", "ml", "count"]),
  description: z.string().optional(),
  min_stock_quantity: z.number().int().min(0).default(0),
});

type FormValues = z.infer<typeof schema>;

function ProductFormModal({
  opened,
  onClose,
  product,
}: {
  opened: boolean;
  onClose: () => void;
  product?: Product;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!product;

  const form = useForm<FormValues>({
    initialValues: {
      name: product?.name ?? "",
      sku: product?.sku ?? "",
      unit_type: (product?.unit_type as FormValues["unit_type"]) ?? "count",
      description: product?.description ?? "",
      min_stock_quantity: product?.min_stock_quantity ?? 0,
    },
    validate: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      isEdit ? productsApi.update(product!.id, values) : productsApi.create(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      notifications.show({
        title: "Success",
        message: `Product ${isEdit ? "updated" : "created"} successfully.`,
        color: "green",
      });
      onClose();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.sku?.[0] || err?.response?.data?.detail || "An error occurred.";
      notifications.show({ title: "Error", message: msg, color: "red" });
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title={isEdit ? "Edit Product" : "New Product"}>
      <form onSubmit={form.onSubmit((v) => mutation.mutate(v))}>
        <Stack>
          <TextInput label="Product Name" placeholder="e.g. Oat Milk" required {...form.getInputProps("name")} />
          <TextInput label="SKU" placeholder="e.g. OAT-001" required {...form.getInputProps("sku")} />
          <Select
            label="Unit Type"
            data={Object.entries(UNIT_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
            required
            {...form.getInputProps("unit_type")}
          />
          <Textarea label="Description" placeholder="Optional description" {...form.getInputProps("description")} />
          <NumberInput
            label="Low Stock Alert Threshold"
            description="Get a warning when stock drops below this quantity (0 = default alert at 5)"
            placeholder="e.g. 10"
            min={0}
            {...form.getInputProps("min_stock_quantity")}
          />
          <Button type="submit" loading={mutation.isPending}>
            {isEdit ? "Save Changes" : "Create Product"}
          </Button>
        </Stack>
      </form>
    </Modal>
  );
}

export default function ProductListPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [unitType, setUnitType] = useState<string | null>(null);
  const [debouncedSearch] = useDebouncedValue(search, 300);
  const [modalOpened, { open, close }] = useDisclosure(false);
  const [editProduct, setEditProduct] = useState<Product | undefined>();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["products", { page, search: debouncedSearch, unit_type: unitType }],
    queryFn: () =>
      productsApi.list({ page, search: debouncedSearch || undefined, unit_type: unitType || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: productsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      notifications.show({ title: "Deleted", message: "Product removed.", color: "green" });
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Cannot delete a product with existing orders.", color: "red" });
    },
  });

  const handleEdit = (product: Product) => {
    setEditProduct(product);
    open();
  };

  const handleNew = () => {
    setEditProduct(undefined);
    open();
  };

  const totalPages = data ? Math.ceil(data.count / 20) : 1;

  return (
    <Stack>
      <PageHeader
        title="Products"
        action={
          <Button leftSection={<IconPlus size={16} />} onClick={handleNew}>
            New Product
          </Button>
        }
      />

      <Group>
        <TextInput
          placeholder="Search by name or SKU…"
          leftSection={<IconSearch size={16} />}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          style={{ flex: 1, maxWidth: 320 }}
        />
        <Select
          placeholder="Filter by unit"
          data={[
            { value: "", label: "All units" },
            ...Object.entries(UNIT_TYPE_LABELS).map(([value, label]) => ({ value, label })),
          ]}
          value={unitType}
          onChange={(v) => { setUnitType(v); setPage(1); }}
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
                <Table.Th>Name</Table.Th>
                <Table.Th>SKU</Table.Th>
                <Table.Th>Unit Type</Table.Th>
                <Table.Th ta="right">Stock</Table.Th>
                <Table.Th ta="center">Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.results.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Center py="xl">
                      <Text c="dimmed">No products found. Create your first product to get started.</Text>
                    </Center>
                  </Table.Td>
                </Table.Tr>
              ) : (
                data?.results.map((product) => (
                  <Table.Tr key={product.id}>
                    <Table.Td fw={500}>{product.name}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" size="sm">{product.sku}</Badge>
                    </Table.Td>
                    <Table.Td>{UNIT_TYPE_LABELS[product.unit_type]}</Table.Td>
                    <Table.Td ta="right">
                      {(() => {
                        const qty = parseFloat(product.total_stock ?? "0");
                        const threshold = product.min_stock_quantity > 0 ? product.min_stock_quantity : 5;
                        const color = qty === 0 ? "red" : qty < threshold ? "yellow" : "teal";
                        const label = qty === 0 ? "Out of stock" : qty < threshold ? "Low" : "OK";
                        return (
                          <Badge color={color} variant="light" size="sm">
                            {product.total_stock ?? "0"} · {label}
                          </Badge>
                        );
                      })()}
                    </Table.Td>
                    <Table.Td>
                      <Group justify="center" gap="xs">
                        <Tooltip label="View details">
                          <ActionIcon
                            variant="light"
                            component={Link}
                            to={`/products/${product.id}`}
                          >
                            <IconEye size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Edit">
                          <ActionIcon variant="light" onClick={() => handleEdit(product)}>
                            <IconEdit size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Delete">
                          <ActionIcon
                            variant="light"
                            color="red"
                            onClick={() => {
                              if (confirm(`Delete "${product.name}"?`)) {
                                deleteMutation.mutate(product.id);
                              }
                            }}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
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

      <ProductFormModal
        key={editProduct?.id ?? "new"}
        opened={modalOpened}
        onClose={() => { close(); setEditProduct(undefined); }}
        product={editProduct}
      />
    </Stack>
  );
}
