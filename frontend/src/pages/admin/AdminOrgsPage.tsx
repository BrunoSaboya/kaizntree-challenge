import {
  ActionIcon,
  Button,
  Group,
  Modal,
  NativeSelect,
  Paper,
  PasswordInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconEdit, IconTrash } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { orgsApi } from "@/api/organizations";
import { usersApi } from "@/api/users";
import type { CreateOrgPayload, Organization, ProvisionOrgPayload } from "@/types/auth";

export default function AdminOrgsPage() {
  const qc = useQueryClient();
  const { data: orgs = [], isLoading } = useQuery({ queryKey: ["organizations"], queryFn: orgsApi.list });
  const { data: users = [] } = useQuery({ queryKey: ["admin-users"], queryFn: usersApi.list });

  const [modalOpen, { open, close }] = useDisclosure(false);
  const [editOrg, setEditOrg] = useState<Organization | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Organization | null>(null);

  // Edit-mode fields
  const [name, setName] = useState("");
  const [ownerId, setOwnerId] = useState<number | "">("");

  // Create-mode (provision) fields
  const [ownerEmail, setOwnerEmail] = useState("");
  const [ownerUsername, setOwnerUsername] = useState("");
  const [ownerPassword, setOwnerPassword] = useState("");
  const [ownerFirstName, setOwnerFirstName] = useState("");
  const [ownerLastName, setOwnerLastName] = useState("");

  function openCreate() {
    setEditOrg(null);
    setName("");
    setOwnerId("");
    setOwnerEmail("");
    setOwnerUsername("");
    setOwnerPassword("");
    setOwnerFirstName("");
    setOwnerLastName("");
    open();
  }

  function openEdit(o: Organization) {
    setEditOrg(o);
    setName(o.name);
    setOwnerId(o.owner);
    open();
  }

  const provisionMutation = useMutation({
    mutationFn: (payload: ProvisionOrgPayload) => orgsApi.provision(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["organizations"] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      close();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<CreateOrgPayload> }) =>
      orgsApi.update(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["organizations"] }); close(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => orgsApi.deleteOrg(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["organizations"] });
      setDeleteTarget(null);
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail ?? "Failed to delete organization.";
      notifications.show({ color: "red", title: "Cannot delete", message: detail });
      setDeleteTarget(null);
    },
  });

  function handleSave() {
    if (editOrg) {
      if (!name || ownerId === "") return;
      updateMutation.mutate({ id: editOrg.id, payload: { name, owner: Number(ownerId) } });
    } else {
      if (!name || !ownerEmail || !ownerUsername || !ownerPassword) return;
      provisionMutation.mutate({
        name,
        owner_email: ownerEmail,
        owner_username: ownerUsername,
        owner_password: ownerPassword,
        owner_first_name: ownerFirstName || undefined,
        owner_last_name: ownerLastName || undefined,
      });
    }
  }

  const isSaving = provisionMutation.isPending || updateMutation.isPending;
  const ownerOptions = users.filter((u) => u.role === "owner" || u.role === "admin");

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={3}>Organizations</Title>
        <Button onClick={openCreate}>New Organization</Button>
      </Group>

      <Paper withBorder radius="md" p={0}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Owner</Table.Th>
              <Table.Th>Created</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr><Table.Td colSpan={4}><Text ta="center" c="dimmed">Loading…</Text></Table.Td></Table.Tr>
            ) : orgs.length === 0 ? (
              <Table.Tr><Table.Td colSpan={4}><Text ta="center" c="dimmed">No organizations found.</Text></Table.Td></Table.Tr>
            ) : orgs.map((o) => (
              <Table.Tr key={o.id}>
                <Table.Td>{o.name}</Table.Td>
                <Table.Td>{o.owner_email}</Table.Td>
                <Table.Td>{new Date(o.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <ActionIcon variant="subtle" onClick={() => openEdit(o)}><IconEdit size={16} /></ActionIcon>
                    <ActionIcon variant="subtle" color="red" onClick={() => setDeleteTarget(o)}>
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal
        opened={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Organization"
        size="sm"
      >
        <Stack>
          <Text>
            Are you sure you want to delete{" "}
            <Text span fw={600}>{deleteTarget?.name}</Text>? This cannot be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button color="red" loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}>
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={modalOpen}
        onClose={close}
        title={editOrg ? "Edit Organization" : "New Organization"}
        size="sm"
      >
        <Stack>
          <TextInput
            label="Organization Name"
            required
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
          />

          {editOrg ? (
            <NativeSelect
              label="Owner"
              required
              value={String(ownerId)}
              onChange={(e) => setOwnerId(e.currentTarget.value === "" ? "" : Number(e.currentTarget.value))}
              data={[
                { value: "", label: "— Select owner —" },
                ...ownerOptions.map((u) => ({ value: String(u.id), label: `${u.email} (${u.role})` })),
              ]}
            />
          ) : (
            <>
              <TextInput
                label="Owner Email"
                required
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.currentTarget.value)}
              />
              <TextInput
                label="Owner Username"
                required
                value={ownerUsername}
                onChange={(e) => setOwnerUsername(e.currentTarget.value)}
              />
              <PasswordInput
                label="Owner Password"
                required
                value={ownerPassword}
                onChange={(e) => setOwnerPassword(e.currentTarget.value)}
              />
              <TextInput
                label="Owner First Name"
                value={ownerFirstName}
                onChange={(e) => setOwnerFirstName(e.currentTarget.value)}
              />
              <TextInput
                label="Owner Last Name"
                value={ownerLastName}
                onChange={(e) => setOwnerLastName(e.currentTarget.value)}
              />
            </>
          )}

          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button
              onClick={handleSave}
              loading={isSaving}
              disabled={
                editOrg
                  ? !name || ownerId === ""
                  : !name || !ownerEmail || !ownerUsername || !ownerPassword
              }
            >
              {editOrg ? "Save" : "Create"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
