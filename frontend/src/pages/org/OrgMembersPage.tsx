import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  Paper,
  PasswordInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconEdit, IconUserOff } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { membersApi } from "@/api/users";
import type { OrgMember } from "@/types/auth";

export default function OrgMembersPage() {
  const qc = useQueryClient();
  const { data: members = [], isLoading } = useQuery({
    queryKey: ["org-members"],
    queryFn: membersApi.list,
  });

  const [modalOpen, { open, close }] = useDisclosure(false);
  const [editMember, setEditMember] = useState<OrgMember | null>(null);

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");

  function openCreate() {
    setEditMember(null);
    setEmail(""); setUsername(""); setFirstName(""); setLastName(""); setPassword("");
    open();
  }

  function openEdit(m: OrgMember) {
    setEditMember(m);
    setEmail(m.email);
    setUsername(m.username);
    setFirstName(m.first_name);
    setLastName(m.last_name);
    setPassword("");
    open();
  }

  const createMutation = useMutation({
    mutationFn: membersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["org-members"] }); close(); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: object }) => membersApi.update(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["org-members"] }); close(); },
  });

  const deactivateMutation = useMutation({
    mutationFn: membersApi.deactivate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org-members"] }),
  });

  function handleSave() {
    if (editMember) {
      const payload: { first_name?: string; last_name?: string; password?: string } = {
        first_name: firstName,
        last_name: lastName,
      };
      if (password) payload.password = password;
      updateMutation.mutate({ id: editMember.id, payload });
    } else {
      createMutation.mutate({ email, username, first_name: firstName, last_name: lastName, password });
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={3}>Members</Title>
        <Button onClick={openCreate}>Add Member</Button>
      </Group>

      <Paper withBorder radius="md" p={0}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Email</Table.Th>
              <Table.Th>Username</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr><Table.Td colSpan={5}><Text ta="center" c="dimmed">Loading…</Text></Table.Td></Table.Tr>
            ) : members.length === 0 ? (
              <Table.Tr><Table.Td colSpan={5}><Text ta="center" c="dimmed">No members yet.</Text></Table.Td></Table.Tr>
            ) : members.map((m) => (
              <Table.Tr key={m.id} style={{ opacity: !m.is_active ? 0.5 : 1 }}>
                <Table.Td>{m.email}</Table.Td>
                <Table.Td>{m.username}</Table.Td>
                <Table.Td>{[m.first_name, m.last_name].filter(Boolean).join(" ") || "—"}</Table.Td>
                <Table.Td>
                  <Badge color={m.is_active ? "green" : "red"} variant="dot" size="sm">
                    {m.is_active ? "Active" : "Inactive"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" justify="flex-end">
                    <ActionIcon variant="subtle" onClick={() => openEdit(m)}><IconEdit size={16} /></ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      onClick={() => deactivateMutation.mutate(m.id)}
                      disabled={!m.is_active}
                    >
                      <IconUserOff size={16} />
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      <Modal
        opened={modalOpen}
        onClose={close}
        title={editMember ? "Edit Member" : "Add Member"}
        size="sm"
      >
        <Stack>
          {!editMember && (
            <>
              <TextInput label="Email" required value={email} onChange={(e) => setEmail(e.currentTarget.value)} />
              <TextInput label="Username" required value={username} onChange={(e) => setUsername(e.currentTarget.value)} />
              <PasswordInput label="Password" required value={password} onChange={(e) => setPassword(e.currentTarget.value)} />
            </>
          )}
          <TextInput label="First Name" value={firstName} onChange={(e) => setFirstName(e.currentTarget.value)} />
          <TextInput label="Last Name" value={lastName} onChange={(e) => setLastName(e.currentTarget.value)} />
          {editMember && (
            <PasswordInput
              label="New Password"
              placeholder="Leave blank to keep current"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
            />
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button onClick={handleSave} loading={isSaving}>
              {editMember ? "Save" : "Add"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
