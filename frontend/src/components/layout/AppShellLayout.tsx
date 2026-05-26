import {
  AppShell,
  Avatar,
  Burger,
  Group,
  Menu,
  NavLink,
  Stack,
  Text,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconBox,
  IconHome,
  IconLogout,
  IconPackage,
  IconShoppingCart,
  IconTruckDelivery,
} from "@tabler/icons-react";
import logo from "@/assets/kaizntree_logo.svg";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

const navLinks = [
  { to: "/", label: "Dashboard", icon: <IconHome size={18} /> },
  { to: "/products", label: "Products", icon: <IconBox size={18} /> },
  { to: "/stock", label: "Stock", icon: <IconPackage size={18} /> },
  { to: "/purchase-orders", label: "Purchase Orders", icon: <IconTruckDelivery size={18} /> },
  { to: "/sales-orders", label: "Sales Orders", icon: <IconShoppingCart size={18} /> },
];

export function AppShellLayout() {
  const [opened, { toggle }] = useDisclosure();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, clearAuth } = useAuthStore();
  const queryClient = useQueryClient();

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      clearAuth();
      queryClient.clear();
      navigate("/login");
    },
  });

  return (
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
              <img src={logo} alt="Kaizntree logo" width={28} height={28} style={{ borderRadius: '50%' }} />
              <Title order={4} fw={700} c="#002c10">
                Kaizntree
              </Title>
            </Group>
          </Group>
          <Menu shadow="md" width={200}>
            <Menu.Target>
              <UnstyledButton>
                <Group gap="xs">
                  <Avatar size="sm" color="brand" radius="xl">
                    {user?.username?.[0]?.toUpperCase() ?? "U"}
                  </Avatar>
                  <Text size="sm" visibleFrom="sm">
                    {user?.username}
                  </Text>
                </Group>
              </UnstyledButton>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>{user?.email}</Menu.Label>
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
              onClick={() => { navigate(to); toggle(); }}
              style={{ borderRadius: "var(--mantine-radius-sm)" }}
            />
          ))}
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
