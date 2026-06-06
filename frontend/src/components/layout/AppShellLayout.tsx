import {
  AppShell,
  Avatar,
  Badge,
  Burger,
  Group,
  Menu,
  Modal,
  NavLink,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconBox,
  IconBrain,
  IconBuilding,
  IconChartBar,
  IconHome,
  IconLogout,
  IconPackage,
  IconPlugConnected,
  IconSettings,
  IconShoppingCart,
  IconTruckDelivery,
  IconUser,
  IconUserPlus,
  IconUsers,
} from "@tabler/icons-react";
import logo from "@/assets/kaizntree_logo.svg";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";

import { authApi } from "@/api/auth";
import api from "@/api/client";
import { useAuthStore } from "@/store/authStore";
import { useRole } from "@/hooks/useRole";

const businessLinks = [
  { to: "/", label: "Dashboard", icon: <IconHome size={18} /> },
  { to: "/products", label: "Products", icon: <IconBox size={18} /> },
  { to: "/stock", label: "Stock", icon: <IconPackage size={18} /> },
  { to: "/purchase-orders", label: "Purchase Orders", icon: <IconTruckDelivery size={18} /> },
  { to: "/sales-orders", label: "Sales Orders", icon: <IconShoppingCart size={18} /> },
  { to: "/suppliers", label: "Suppliers", icon: <IconUsers size={18} /> },
  { to: "/forecasting", label: "Forecasting", icon: <IconChartBar size={18} /> },
  { to: "/ai-assist", label: "AI Assistant", icon: <IconBrain size={18} /> },
  { to: "/integrations", label: "Integrations", icon: <IconPlugConnected size={18} /> },
];

const ownerLinks = [
  { to: "/org/members", label: "Members", icon: <IconUserPlus size={18} /> },
];

const adminLinks = [
  { to: "/admin/users", label: "Users", icon: <IconUser size={18} /> },
  { to: "/admin/organizations", label: "Organizations", icon: <IconBuilding size={18} /> },
];

const roleBadgeColor: Record<string, string> = {
  admin: "red",
  owner: "brand",
  member: "gray",
};

export function AppShellLayout() {
  const [opened, { toggle }] = useDisclosure();
  const [profileOpen, { open: openProfile, close: closeProfile }] = useDisclosure(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, clearAuth, setAuth } = useAuthStore();
  const queryClient = useQueryClient();
  const { isAdmin, isOwner, role } = useRole();

  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [password, setPassword] = useState("");

  const navLinks = isAdmin
    ? adminLinks
    : [...businessLinks, ...(isOwner ? ownerLinks : [])];

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      clearAuth();
      queryClient.clear();
      navigate("/login");
    },
  });

  const profileMutation = useMutation({
    mutationFn: (payload: { first_name?: string; last_name?: string; password?: string }) =>
      api.patch("/auth/me/", payload).then((r) => r.data),
    onSuccess: (updatedUser) => {
      if (user) {
        setAuth(useAuthStore.getState().accessToken!, { ...user, ...updatedUser });
      }
      setPassword("");
      closeProfile();
    },
  });

  function handleProfileSave() {
    const payload: { first_name?: string; last_name?: string; password?: string } = {
      first_name: firstName,
      last_name: lastName,
    };
    if (password) payload.password = password;
    profileMutation.mutate(payload);
  }

  return (
    <>
      <AppShell
        header={{ height: 60 }}
        navbar={{ width: 240, breakpoint: "sm", collapsed: { mobile: !opened } }}
        padding="md"
        styles={{
          header: { backgroundColor: "#fcf6ef" },
          navbar: { backgroundColor: "#fcf6ef" },
          main: { backgroundColor: "#fcf6ef" },
        }}
      >
        <AppShell.Header>
          <Group h="100%" px="md" justify="space-between">
            <Group>
              <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
              <Group gap="xs">
                <img src={logo} alt="Kaizntree logo" width={28} height={28} style={{ borderRadius: "50%" }} />
                <Title order={4} fw={700} c="#002c10">
                  {user?.organization_name ?? "Kaizntree"}
                </Title>
              </Group>
            </Group>
            <Menu shadow="md" width={220}>
              <Menu.Target>
                <UnstyledButton>
                  <Group gap="xs">
                    <Avatar size="sm" color="brand" radius="xl">
                      {user?.username?.[0]?.toUpperCase() ?? "U"}
                    </Avatar>
                    <Stack gap={0} visibleFrom="sm">
                      <Text size="sm" lh={1.2}>
                        {user?.username}
                      </Text>
                      {role && (
                        <Badge size="xs" color={roleBadgeColor[role] ?? "gray"} variant="light">
                          {role}
                        </Badge>
                      )}
                    </Stack>
                  </Group>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>
                  {user?.email}
                  {user?.organization_name && (
                    <Text size="xs" c="dimmed">
                      {user.organization_name}
                    </Text>
                  )}
                </Menu.Label>
                <Menu.Item
                  leftSection={<IconSettings size={16} />}
                  onClick={openProfile}
                >
                  Edit Profile
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item
                  leftSection={<IconLogout size={16} />}
                  color="red"
                  onClick={() => logoutMutation.mutate()}
                >
                  Logout
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="sm">
          <Stack gap={4}>
            {navLinks.map(({ to, label, icon }) => (
              <NavLink
                key={to}
                label={label}
                leftSection={icon}
                active={to === "/" ? pathname === "/" : pathname.startsWith(to)}
                onClick={() => {
                  navigate(to);
                  toggle();
                }}
                style={{ borderRadius: "var(--mantine-radius-sm)" }}
              />
            ))}
          </Stack>
        </AppShell.Navbar>

        <AppShell.Main>
          <Outlet />
        </AppShell.Main>
      </AppShell>

      <Modal opened={profileOpen} onClose={closeProfile} title="Edit Profile">
        <Stack>
          <TextInput
            label="First Name"
            value={firstName}
            onChange={(e) => setFirstName(e.currentTarget.value)}
          />
          <TextInput
            label="Last Name"
            value={lastName}
            onChange={(e) => setLastName(e.currentTarget.value)}
          />
          <PasswordInput
            label="New Password"
            placeholder="Leave blank to keep current password"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <UnstyledButton onClick={closeProfile}>Cancel</UnstyledButton>
            <button
              onClick={handleProfileSave}
              disabled={profileMutation.isPending}
              style={{
                background: "#002c10",
                color: "white",
                border: "none",
                borderRadius: 4,
                padding: "6px 16px",
                cursor: "pointer",
              }}
            >
              {profileMutation.isPending ? "Saving..." : "Save"}
            </button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
