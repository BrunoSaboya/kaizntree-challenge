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

const schema = z
  .object({
    email: z.string().email("Invalid email address"),
    username: z.string().min(2, "Username must be at least 2 characters"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    password_confirm: z.string(),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Passwords do not match",
    path: ["password_confirm"],
  });

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const form = useForm({
    initialValues: { email: "", username: "", password: "", password_confirm: "" },
    validate: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: ({ access, user }) => {
      setAuth(access, user);
      navigate("/");
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.email?.[0] || "Registration failed. Please try again.";
      notifications.show({ title: "Error", message: detail, color: "red" });
    },
  });

  return (
    <Center style={{ minHeight: "100vh" }} bg="gray.0">
      <Box w={440} p="md">
        <Stack align="center" mb="xl">
          <Title order={2}>Create your account</Title>
          <Text c="dimmed" size="sm">
            Start managing your inventory with Kaizntree
          </Text>
        </Stack>
        <Paper shadow="sm" p="xl" radius="md">
          <form onSubmit={form.onSubmit((values) => mutation.mutate(values))}>
            <Stack>
              <TextInput label="Email" placeholder="you@example.com" {...form.getInputProps("email")} />
              <TextInput label="Username" placeholder="yourname" {...form.getInputProps("username")} />
              <PasswordInput label="Password" placeholder="At least 8 characters" {...form.getInputProps("password")} />
              <PasswordInput label="Confirm Password" placeholder="Repeat password" {...form.getInputProps("password_confirm")} />
              <Button type="submit" loading={mutation.isPending} fullWidth mt="sm">
                Create account
              </Button>
            </Stack>
          </form>
        </Paper>
        <Text ta="center" mt="md" size="sm">
          Already have an account?{" "}
          <Anchor component={Link} to="/login">
            Sign in
          </Anchor>
        </Text>
      </Box>
    </Center>
  );
}
