// IMPORTANT: When adding new env variables to the codebase, update this array
export const ENV_VARIABLES: EnvVariable[] = [
  // Supabase Database Variables (for Python backend)
  {
    name: "NEXT_PUBLIC_SUPABASE_URL",
    description: "Supabase project URL for Python backend database operations",
    required: true,
    instructions: "Go to [Supabase Dashboard](https://supabase.com/dashboard) → Your Project → Settings → Data API → Copy the 'Project URL -> URL' field (format: https://[project-id].supabase.co)"
  },
  {
    name: "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    description: "Supabase anonymous key for Python backend database access",
    required: true,
    instructions: "Go to [Supabase Dashboard](https://supabase.com/dashboard) → Your Project → Settings → API Keys → Copy 'Legacy API keys → anon public' key"
  },
  {
    name: "SUPABASE_SERVICE_ROLE_KEY",
    description: "Supabase service role key for privileged operations",
    required: false,
    instructions: "Optional: Settings → API Keys → Copy 'service_role' key if running with elevated permissions"
  },
  // Python Backend API Keys
  {
    name: "TELEGRAM_BOT_TOKEN",
    description: "Telegram Bot API token for skin health tracker bot",
    required: true,
    instructions: "1. Open Telegram and search for @BotFather\n2. Send /newbot command\n3. Follow instructions to create a bot\n4. Copy the HTTP API token provided\n5. Paste the token here (format: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)"
  },
  {
    name: "OPENAI_API_KEY",
    description: "OpenAI API key for GPT-4 skin health analysis and insights",
    required: true,
    instructions: "1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)\n2. Create an account or log in\n3. Click 'Create new secret key'\n4. Copy the API key (starts with sk-)\n5. Make sure you have billing set up for API usage"
  },
  {
    name: "BASE_URL",
    description: "Public base URL where the FastAPI server is accessible",
    required: false,
    instructions: "Set to the externally reachable URL of the backend (e.g., https://example.ngrok.io)"
  }
];

// Next.js compatibility variables (optional)
// {
//   name: "DATABASE_URL",
//   description: "Supabase PostgreSQL database connection string for migrations and server-side operations",
//   required: false,
//   instructions: "Go to [Supabase Dashboard](https://supabase.com/dashboard) → Your Project → Settings → Database → Connection string (URI format).\n Copy the full postgresql:// connection string.\n Make sure to replace [YOUR-PASSWORD] with actual password"
// }

export interface EnvVariable {
  name: string
  description: string
  instructions: string
  required: boolean
}

export function checkMissingEnvVars(): string[] {
  return ENV_VARIABLES.filter(envVar => envVar.required && !process.env[envVar.name]).map(envVar => envVar.name)
}