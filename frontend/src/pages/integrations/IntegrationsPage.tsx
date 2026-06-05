import {
  Badge,
  Card,
  Code,
  Divider,
  Grid,
  Group,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconBrandAmazon,
  IconCheck,
  IconPlugConnected,
  IconPlugConnectedX,
  IconShoppingBag,
  IconX,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";

import api from "@/api/client";
import { PageHeader } from "@/components/common/PageHeader";

interface IntegrationStatus {
  shopify: boolean;
  amazon: boolean;
  quickbooks: boolean;
  netsuite: boolean;
}

function fetchIntegrationStatus(): Promise<IntegrationStatus> {
  return api.get<IntegrationStatus>("/integrations/status/").then((r) => r.data);
}

interface PlatformCardProps {
  name: string;
  description: string;
  icon: React.ReactNode;
  configured: boolean;
  envVars: string[];
  docsUrl?: string;
  endpointNote?: string;
}

function PlatformCard({
  name,
  description,
  icon,
  configured,
  envVars,
  endpointNote,
}: PlatformCardProps) {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="sm">
        <Group justify="space-between">
          <Group gap="sm">
            <ThemeIcon
              size="lg"
              radius="md"
              color={configured ? "teal" : "gray"}
              variant="light"
            >
              {icon}
            </ThemeIcon>
            <div>
              <Text fw={600}>{name}</Text>
              <Text fz="xs" c="dimmed">{description}</Text>
            </div>
          </Group>
          <Badge
            color={configured ? "teal" : "gray"}
            variant="light"
            leftSection={configured ? <IconCheck size={12} /> : <IconX size={12} />}
          >
            {configured ? "Connected" : "Not configured"}
          </Badge>
        </Group>

        <Divider />

        <Stack gap={4}>
          <Text fz="xs" fw={500} c="dimmed">Required .env variables</Text>
          {envVars.map((v) => (
            <Code key={v} fz="xs">{v}</Code>
          ))}
        </Stack>

        {endpointNote && (
          <Text fz="xs" c="dimmed" mt={4}>
            {endpointNote}
          </Text>
        )}
      </Stack>
    </Card>
  );
}

const PLATFORMS: Omit<PlatformCardProps, "configured">[] = [
  {
    name: "Shopify",
    description: "Ingest orders as draft Sales Orders via webhook",
    icon: <IconShoppingBag size={18} />,
    envVars: [
      "SHOPIFY_WEBHOOK_SECRET",
      "SHOPIFY_SHOP_DOMAIN",
      "SHOPIFY_ACCESS_TOKEN",
    ],
    endpointNote:
      "Webhook receiver: POST /api/v1/integrations/shopify/webhook/ — register this URL in Shopify Admin > Settings > Notifications > Webhooks (topic: orders/create). Authentication uses HMAC-SHA256, not JWT.",
  },
  {
    name: "Amazon",
    description: "SP-API order polling and inventory sync",
    icon: <IconBrandAmazon size={18} />,
    envVars: [
      "AMAZON_SELLER_ID",
      "AMAZON_LWA_CLIENT_ID",
      "AMAZON_LWA_CLIENT_SECRET",
      "AMAZON_LWA_REFRESH_TOKEN",
      "AMAZON_AWS_ACCESS_KEY",
      "AMAZON_AWS_SECRET_KEY",
    ],
    endpointNote:
      "Credentials from: Seller Central > Apps & Services > Develop Apps. Requires an IAM role with AmazonSellerPartnerAPIExecutionPolicy.",
  },
  {
    name: "QuickBooks Online",
    description: "Sync confirmed POs as Bills, suppliers as Vendors",
    icon: <IconPlugConnected size={18} />,
    envVars: [
      "QUICKBOOKS_CLIENT_ID",
      "QUICKBOOKS_CLIENT_SECRET",
      "QUICKBOOKS_REALM_ID",
      "QUICKBOOKS_ACCESS_TOKEN",
      "QUICKBOOKS_REFRESH_TOKEN",
    ],
    endpointNote:
      "OAuth 2.0 — get credentials at developer.intuit.com. QUICKBOOKS_REALM_ID is the company ID returned in the OAuth callback. Set QUICKBOOKS_ENVIRONMENT=production for live data.",
  },
  {
    name: "NetSuite",
    description: "Sync confirmed POs as VendorBills, suppliers as Vendors",
    icon: <IconPlugConnectedX size={18} />,
    envVars: [
      "NETSUITE_ACCOUNT_ID",
      "NETSUITE_CONSUMER_KEY",
      "NETSUITE_CONSUMER_SECRET",
      "NETSUITE_TOKEN_ID",
      "NETSUITE_TOKEN_SECRET",
    ],
    endpointNote:
      "Token-Based Authentication (TBA / OAuth 1.0a). Credentials from: NetSuite Admin > Setup > Integration > Manage Integrations. Set NETSUITE_SUBSIDIARY_ID for OneWorld accounts.",
  },
];

const STATUS_KEYS: (keyof IntegrationStatus)[] = [
  "shopify",
  "amazon",
  "quickbooks",
  "netsuite",
];

export default function IntegrationsPage() {
  const { data: status, isLoading } = useQuery({
    queryKey: ["integration-status"],
    queryFn: fetchIntegrationStatus,
  });

  const configuredCount = status
    ? STATUS_KEYS.filter((k) => status[k]).length
    : 0;

  return (
    <Stack>
      <PageHeader
        title="Integrations"
        action={
          <Badge color={configuredCount > 0 ? "teal" : "gray"} size="lg" variant="light">
            {isLoading ? "…" : `${configuredCount} / ${PLATFORMS.length} connected`}
          </Badge>
        }
      />

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Group gap="xs" mb="xs">
          <ThemeIcon size="sm" color="brand" variant="light">
            <IconPlugConnected size={14} />
          </ThemeIcon>
          <Title order={6}>About integrations</Title>
        </Group>
        <Text fz="sm" c="dimmed">
          Kaizntree connects to e-commerce platforms (Shopify, Amazon) and ERP systems
          (QuickBooks, NetSuite) through an adapter layer. Each integration is activated
          by setting the corresponding environment variables in your <Code fz="xs">.env</Code> file
          and rebuilding the backend container. No credentials → the integration is silently
          disabled with no error.
        </Text>
      </Card>

      <Grid>
        {PLATFORMS.map((platform, i) => {
          const key = STATUS_KEYS[i];
          const configured = status ? status[key] : false;
          return (
            <Grid.Col key={platform.name} span={{ base: 12, md: 6 }}>
              <PlatformCard {...platform} configured={configured} />
            </Grid.Col>
          );
        })}
      </Grid>
    </Stack>
  );
}
