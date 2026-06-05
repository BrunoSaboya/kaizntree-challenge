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
  Stack,
  Switch,
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconEdit, IconPlus, IconTrash } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { suppliersApi } from "@/api/suppliers";
import { PageHeader } from "@/components/common/PageHeader";
import type { Supplier } from "@/types/supplier";

interface SupplierFormValues {
  name: string;
  email: string;
  phone: string;
  address: string;
  payment_terms: string;
  lead_time_days: number;
  notes: string;
  active: boolean;
}

const defaultValues: SupplierFormValues = {
  name: "",
  email: "",
  phone: "",
  address: "",
  payment_terms: "Net30",
  lead_time_days: 7,
  notes: "",
  active: true,
};

function SupplierModal({
  opened,
  onClose,
  supplier,
}: {
  opened: boolean;
  onClose: () => void;
  supplier?: Supplier;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!supplier;

  const form = useForm<SupplierFormValues>({
    initialValues: supplier
      ? {
          name: supplier.name,
          email: supplier.email,
          phone: supplier.phone,
          address: supplier.address,
          payment_terms: supplier.payment_terms,
          lead_time_days: supplier.lead_time_days,
          notes: supplier.notes,
          active: supplier.active,
        }
      : defaultValues,
    validate: {
      name: (v) => (!v.trim() ? "Name is required" : null),
      lead_time_days: (v) => (v < 0 ? "Must be ≥ 0" : null),
    },
  });

  const mutation = useMutation({
    mutationFn: (values: SupplierFormValues) =>
      isEdit
        ? suppliersApi.update(supplier!.id, values)
        : suppliersApi.create(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      notifications.show({
        title: isEdit ? "Updated" : "Created",
        message: `Supplier ${isEdit ? "updated" : "created"} successfully.`,
        color: "green",
      });
      form.reset();
      onClose();
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Failed to save supplier.", color: "red" });
    },
  });

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEdit ? "Edit Supplier" : "New Supplier"}
      size="md"
    >
      <form onSubmit={form.onSubmit((v) => mutation.mutate(v))}>
        <Stack>
          <TextInput label="Name" placeholder="Acme Farms" required {...form.getInputProps("name")} />
          <Group grow>
            <TextInput label="Email" placeholder="orders@supplier.com" {...form.getInputProps("email")} />
            <TextInput label="Phone" placeholder="+1-555-0100" {...form.getInputProps("phone")} />
          </Group>
          <TextInput label="Address" placeholder="123 Farm Rd, City, State" {...form.getInputProps("address")} />
          <Group grow>
            <TextInput label="Payment Terms" placeholder="Net30" {...form.getInputProps("payment_terms")} />
            <NumberInput
              label="Lead Time (days)"
              min={0}
              {...form.getInputProps("lead_time_days")}
            />
          </Group>
          <Textarea label="Notes" placeholder="Additional notes…" {...form.getInputProps("notes")} />
          <Switch label="Active" {...form.getInputProps("active", { type: "checkbox" })} />
          <Button type="submit" loading={mutation.isPending}>
            {isEdit ? "Save Changes" : "Create Supplier"}
          </Button>
        </Stack>
      </form>
    </Modal>
  );
}

export default function SuppliersPage() {
  const [page, setPage] = useState(1);
  const [editSupplier, setEditSupplier] = useState<Supplier | undefined>();
  const [newOpened, { open: openNew, close: closeNew }] = useDisclosure(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", { page }],
    queryFn: () => suppliersApi.list({ page }),
  });

  const deleteMutation = useMutation({
    mutationFn: suppliersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      notifications.show({ title: "Deleted", message: "Supplier removed.", color: "orange" });
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Cannot delete supplier.", color: "red" });
    },
  });

  const totalPages = data ? Math.ceil(data.count / 20) : 1;

  return (
    <Stack>
      <PageHeader
        title="Suppliers"
        action={
          <Button leftSection={<IconPlus size={16} />} onClick={openNew}>
            New Supplier
          </Button>
        }
      />

      {isLoading ? (
        <Center h={200}>
          <Loader />
        </Center>
      ) : (
        <Card shadow="sm" padding={0} radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>Contact</Table.Th>
                <Table.Th ta="center">Lead Time</Table.Th>
                <Table.Th>Payment Terms</Table.Th>
                <Table.Th ta="center">Status</Table.Th>
                <Table.Th ta="center">Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.results.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={6}>
                    <Center py="xl">
                      <Text c="dimmed">No suppliers yet. Add your first supplier to get started.</Text>
                    </Center>
                  </Table.Td>
                </Table.Tr>
              ) : (
                data?.results.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td fw={500}>{s.name}</Table.Td>
                    <Table.Td>
                      <Stack gap={0}>
                        {s.email && <Text size="sm">{s.email}</Text>}
                        {s.phone && <Text size="xs" c="dimmed">{s.phone}</Text>}
                      </Stack>
                    </Table.Td>
                    <Table.Td ta="center">
                      <Badge variant="light" color="blue">
                        {s.lead_time_days}d
                      </Badge>
                    </Table.Td>
                    <Table.Td>{s.payment_terms || "—"}</Table.Td>
                    <Table.Td ta="center">
                      <Badge color={s.active ? "green" : "gray"} variant="light">
                        {s.active ? "Active" : "Inactive"}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group justify="center" gap="xs">
                        <Button
                          size="xs"
                          variant="light"
                          leftSection={<IconEdit size={14} />}
                          onClick={() => setEditSupplier(s)}
                        >
                          Edit
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          leftSection={<IconTrash size={14} />}
                          onClick={() => deleteMutation.mutate(s.id)}
                          loading={deleteMutation.isPending}
                        >
                          Delete
                        </Button>
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

      <SupplierModal opened={newOpened} onClose={closeNew} />
      {editSupplier && (
        <SupplierModal
          opened={!!editSupplier}
          onClose={() => setEditSupplier(undefined)}
          supplier={editSupplier}
        />
      )}
    </Stack>
  );
}
