import {
  Anchor,
  Box,
  Button,
  Center,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { zodResolver } from "mantine-form-zod-resolver";
import { z } from "zod";

import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

const schema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

export default function LoginPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: ({ access, user }) => {
      setAuth(access, user);
      navigate("/");
    },
    onError: () => {
      notifications.show({
        title: "Login failed",
        message: "Invalid email or password.",
        color: "red",
      });
    },
  });

  return (
    <Center style={{ minHeight: "100vh" }} bg="gray.0">
      <Box w={420} p="md">
        <Stack align="center" mb="xl">
          <Title order={2}>Welcome back</Title>
          <Text c="dimmed" size="sm">
            Sign in to your Kaizntree account
          </Text>
        </Stack>
        <Paper shadow="sm" p="xl" radius="md">
          <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
            <Stack>
              <TextInput
                label="Email"
                placeholder="you@example.com"
                {...form.getInputProps("email")}
              />
              <PasswordInput
                label="Password"
                placeholder="Your password"
                {...form.getInputProps("password")}
              />
              <Button type="submit" loading={mutation.isPending} fullWidth mt="sm">
                Sign in
              </Button>
            </Stack>
          </form>
        </Paper>
        <Text ta="center" mt="md" size="sm">
          Don&apos;t have an account?{" "}
          <Anchor component={Link} to="/register">
            Create one
          </Anchor>
        </Text>
      </Box>
    </Center>
  );
}
