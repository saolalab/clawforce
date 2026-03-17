import { useState } from "react";
import { Button } from "../ui";
import { SiTelegram, SiDiscord, SiWhatsapp, SiSlack } from "react-icons/si";
import { MdEmail } from "react-icons/md";

// Custom icons for platforms not in react-icons
const FeishuIcon = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="5" fill="#336FFF" />
    <path
      d="M8 17.5C9.5 15 11 13 12 11.5C13 13 14.5 15 16 17.5H13.5C13 16 12.7 15 12 13.8C11.3 15 11 16 10.5 17.5H8Z"
      fill="white"
    />
    <path
      d="M12 6.5C10.5 6.5 9.5 7.5 9.5 9C9.5 10.5 10.5 11.5 12 11.5C13.5 11.5 14.5 10.5 14.5 9C14.5 7.5 13.5 6.5 12 6.5Z"
      fill="white"
    />
  </svg>
);

interface ChannelConfigurationProps {
  channels: Record<string, Record<string, unknown>>;
  onUpdate: (channels: Record<string, Record<string, unknown>>) => void;
  isSaving: boolean;
}

interface ChannelDef {
  key: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  fields: { key: string; label: string; type: string; required?: boolean }[];
}

const CHANNELS: ChannelDef[] = [
  {
    key: "telegram",
    name: "Telegram",
    icon: <SiTelegram className="text-[#26A5E4]" size={20} />,
    description: "Bot token and allowed chat IDs",
    fields: [
      { key: "token", label: "Bot Token", type: "password", required: true },
      { key: "allowFrom", label: "Allowed Chat IDs (comma-separated)", type: "text" },
    ],
  },
  {
    key: "discord",
    name: "Discord",
    icon: <SiDiscord className="text-[#5865F2]" size={20} />,
    description: "Bot token and guild configuration",
    fields: [
      { key: "token", label: "Bot Token", type: "password", required: true },
      { key: "guild_id", label: "Guild ID", type: "text" },
    ],
  },
  {
    key: "slack",
    name: "Slack",
    icon: <SiSlack className="text-[#4A154B]" size={20} />,
    description: "App-level token and signing secret",
    fields: [
      { key: "token", label: "Bot Token", type: "password", required: true },
      { key: "signing_secret", label: "Signing Secret", type: "password" },
    ],
  },
  {
    key: "whatsapp",
    name: "WhatsApp",
    icon: <SiWhatsapp className="text-[#25D366]" size={20} />,
    description: "WhatsApp Business API configuration",
    fields: [
      { key: "phone_number_id", label: "Phone Number ID", type: "text", required: true },
      { key: "access_token", label: "Access Token", type: "password", required: true },
    ],
  },
  {
    key: "email",
    name: "Email",
    icon: <MdEmail className="text-gray-600" size={20} />,
    description: "SMTP and IMAP configuration",
    fields: [
      { key: "smtp_host", label: "SMTP Host", type: "text" },
      { key: "smtp_port", label: "SMTP Port", type: "number" },
      { key: "username", label: "Username", type: "text" },
      { key: "password", label: "Password", type: "password" },
    ],
  },
  {
    key: "feishu",
    name: "Feishu (Lark)",
    icon: <FeishuIcon size={20} />,
    description: "Feishu app credentials",
    fields: [
      { key: "app_id", label: "App ID", type: "text", required: true },
      { key: "app_secret", label: "App Secret", type: "password", required: true },
    ],
  },
];

/**
 * ChannelConfiguration manages messaging platform integrations for the agent.
 * Supports Telegram, Discord, Slack, WhatsApp, Email, and Feishu.
 */
export function ChannelConfiguration({
  channels,
  onUpdate,
  isSaving,
}: ChannelConfigurationProps) {
  const [editingChannel, setEditingChannel] = useState<string | null>(null);
  const [editedConfig, setEditedConfig] = useState<Record<string, unknown>>({});

  const handleEdit = (channelKey: string) => {
    setEditingChannel(channelKey);
    setEditedConfig(channels[channelKey] || {});
  };

  const handleSave = (channelKey: string) => {
    const newChannels = { ...channels };
    if (Object.keys(editedConfig).length === 0) {
      delete newChannels[channelKey];
    } else {
      newChannels[channelKey] = editedConfig;
    }
    onUpdate(newChannels);
    setEditingChannel(null);
    setEditedConfig({});
  };

  const handleCancel = () => {
    setEditingChannel(null);
    setEditedConfig({});
  };

  const updateField = (key: string, value: unknown) => {
    setEditedConfig((prev) => ({ ...prev, [key]: value }));
  };

  const isEnabled = (channelKey: string) => {
    return channelKey in channels && Object.keys(channels[channelKey]).length > 0;
  };

  return (
    <div className="bg-claude-input rounded-xl border border-claude-border">
      <div className="px-4 py-3 border-b border-claude-border">
        <h3 className="text-sm font-semibold text-claude-text-primary">Channels</h3>
        <p className="text-xs text-claude-text-muted mt-0.5">Configure messaging platform integrations</p>
      </div>

      <div className="divide-y divide-claude-border">
        {CHANNELS.map((channel) => {
          const enabled = isEnabled(channel.key);
          const isEditing = editingChannel === channel.key;
          const currentConfig = channels[channel.key] || {};

          return (
            <div key={channel.key} className="px-4 py-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-8 h-8 rounded bg-claude-surface">
                    {channel.icon}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-claude-text-primary">{channel.name}</span>
                      {enabled && (
                        <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">Enabled</span>
                      )}
                    </div>
                    <p className="text-xs text-claude-text-muted mt-0.5">{channel.description}</p>
                  </div>
                </div>

                {isEditing ? (
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={handleCancel}>
                      Cancel
                    </Button>
                    <Button size="sm" onClick={() => handleSave(channel.key)} disabled={isSaving}>
                      {isSaving ? "Saving..." : "Save"}
                    </Button>
                  </div>
                ) : (
                  <Button variant="ghost" size="sm" onClick={() => handleEdit(channel.key)}>
                    {enabled ? "Edit" : "Configure"}
                  </Button>
                )}
              </div>

              {isEditing && (
                <div className="mt-3 p-3 bg-claude-surface rounded-lg space-y-3">
                  {channel.fields.map((field) => (
                    <div key={field.key}>
                      <label className="block text-xs text-claude-text-muted mb-1">
                        {field.label}
                        {field.required && <span className="text-red-500 ml-0.5">*</span>}
                      </label>
                      <input
                        type={field.type}
                        value={(editedConfig[field.key] as string) || ""}
                        onChange={(e) =>
                          updateField(
                            field.key,
                            field.type === "number" ? parseInt(e.target.value, 10) : e.target.value
                          )
                        }
                        className="w-full px-2 py-1.5 text-sm border border-claude-border rounded bg-claude-bg"
                      />
                    </div>
                  ))}

                  {enabled && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => {
                        setEditedConfig({});
                        handleSave(channel.key);
                      }}
                    >
                      Disable Channel
                    </Button>
                  )}
                </div>
              )}

              {!isEditing && enabled && (
                <div className="mt-2 text-xs text-claude-text-secondary">
                  Configured fields: {Object.keys(currentConfig).join(", ")}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
