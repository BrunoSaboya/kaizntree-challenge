import {
  ActionIcon,
  Badge,
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
import { IconEdit, IconUserCheck, IconUserOff } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { orgsApi } from "@/api/organizations";
import { usersApi } from "@/api/users";
import type { CreateUserPayload, User, UserRole } from "@/types/auth";

const roleBadgeColor: Record<string, string> = { admin: "red", owner: "teal", member: "gray" };

export default function AdminUsersPage() {
  const qc = useQueryClient();
  const { data: users = [], isLoading } = useQuery({ queryKey: ["admin-users"], queryFn: usersApi.list });
  const { data: orgs = [] } = useQuery({ queryKey: ["organizations"], queryFn: orgsApi.list });

  const [modalOpen, { open, close }] = useDisclosure(false);
  const [editUser, setEditUser] = useState<User | null>(null);

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState<UserRole>("owner");
  const [orgId, setOrgId] = useState<number | "">("");
  const [password, setPassword] = useState("");

  function resetForm(user?: User) {
    setEmail(user?.email ?? "");
    setUsername(user?.username ?? "");
    setFirstName(user?.first_name ?? "");
    setLastName(user?.last_name ?? "");
    setRole(user?.role ?? "owner");
    setOrgId(user?.organization_id ?? "");
    setPassword("");
  }

  function openCreate() {
    setEditUser(null);
    resetForm();
    open();
  }

  function openEdit(u: User) {
    setEditUser(u);
    resetForm(u);
    open();
  }

  const createMutation = useMutation({
    mutationFn: (payload: CreateUserPayload) => usersApi.create(payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-users"] }); close(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: object }) => usersApi.update(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-users"] }); close(); },
  });

  const deactivateMutation = useMutation({
    mutationFn: usersApi.deactivate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const reactivateMutation = useMutation({
    mutationFn: (id: number) => usersApi.reactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  function handleSave() {
    if (editUser) {
      updateMutation.mutate({
        id: editUser.id,
        payload: {
          first_name: firstName,
          last_name: lastName,
          role,
          organization: orgId === "" ? null : Number(orgId),
        },
      });
    } else {
      createMutation.mutate({
        email,
        username,
        first_name: firstName,
        last_name: lastName,
        role,
        organization: orgId === "" ? null : Number(orgId),
        password,
      });
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={3}>Users</Title>
        <Button onClick={openCreate}>New User</Button>
      </Group>

      <Paper withBorder radius="md" p={0}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Email</Table.Th>
              <Table.Th>Username</Table.Th>
              <Table.Th>Role</Table.Th>
              <Table.Th>Organization</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr><Table.Td colSpan={6}><Text ta="center" c="dimmed">Loading…</Text></Table.Td></Table.Tr>
            ) : users.length === 0 ? (
              <Table.Tr><Table.Td colSpan={6}><Text ta="center" c="dimmed">No users found.</Text></Table.Td></Table.Tr>
            ) : users.map((u) => (
              <Table.Tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.5 }}>
                <Table.Td>{u.email}</Table.Td>
                <Table.Td>{u.username}</Table.Td>
                <Table.Td>
                  <Badge color={roleBadgeColor[u.role] ?? "gray"} variant="light" size="sm">
                    {u.role}
                  </Badge>
                </Table.Td>
                <Table.Td>{u.organization_name ?? "—"}</Table.Td>
                <Table.Td>
                  <Badge color={u.is_active ? "green" : "red"} variant="dot" size="sm">
                    {u.is_active ? "Active" : "Inactive"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {u.role !== "admin" && (
                    <Group gap="xs" justify="flex-end">
                      <ActionIcon variant="subtle" onClick={() => openEdit(u)}>
                        <IconEdit size={16} />
                      </ActionIcon>
                      {u.is_active ? (
                        <ActionIcon variant="subtle" color="red"
                          onClick={() => deactivateMutation.mutate(u.id)}>
                          <IconUserOff size={16} />
                        </ActionIcon>
                      ) : (
                        <ActionIcon variant="subtle" color="green"
                          onClick={() => reactivateMutation.mutate(u.id)}>
                          <IconUserCheck size={16} />
                        </ActionIcon>
                      )}
                    </Group>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal
        opened={modalOpen}
        onClose={close}
        title={editUser ? "Edit User" : "Create User"}
        size="md"
      >
        <Stack>
          {!editUser && (
            <>
              <TextInput label="Email" required value={email} onChange={(e) => setEmail(e.currentTarget.value)} />
              <TextInput label="Username" required value={username} onChange={(e) => setUsername(e.currentTarget.value)} />
              <PasswordInput label="Password" required value={password} onChange={(e) => setPassword(e.currentTarget.value)} />
            </>
          )}
          <TextInput label="First Name" value={firstName} onChange={(e) => setFirstName(e.currentTarget.value)} />
          <TextInput label="Last Name" value={lastName} onChange={(e) => setLastName(e.currentTarget.value)} />
          <NativeSelect
            label="Role"
            value={role}
            onChange={(e) => setRole(e.currentTarget.value as UserRole)}
            data={[
              { value: "owner", label: "Owner" },
              { value: "member", label: "Member" },
            ]}
          />
          {role !== "admin" && (
            <NativeSelect
              label="Organization"
              value={String(orgId)}
              onChange={(e) => setOrgId(e.currentTarget.value === "" ? "" : Number(e.currentTarget.value))}
              data={[
                { value: "", label: "— Select organization —" },
                ...orgs.map((o) => ({ value: String(o.id), label: o.name })),
              ]}
            />
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button onClick={handleSave} loading={isSaving}>
              {editUser ? "Save" : "Create"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
