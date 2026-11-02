import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
export default function (pi: ExtensionAPI) {
  const model = process.env.HOMEWORK_CHAT_MODEL || 'deepseek-flash';
  pi.registerProvider('homework', {
    baseUrl: process.env.HOMEWORK_CHAT_BASE_URL || 'https://api.deepseek.com',
    apiKey: 'DEEPSEEK_API_KEY', api: 'openai-completions',
    models: [{id: model, name: model, reasoning: false, input: ['text'],
      cost: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0}, contextWindow: 128000, maxTokens: 4096}],
  });
}
