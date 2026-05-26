import { Group, Title } from "@mantine/core";
import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  action?: ReactNode;
}

export function PageHeader({ title, action }: PageHeaderProps) {
  return (
    <Group justify="space-between" mb="lg">
      <Title order={2}>{title}</Title>
      {action}
    </Group>
  );
}
