/**
 * Chat model registry.
 *
 * One place that defines every model the picker offers. `supportsTools` is the
 * important bit: models that speak the OpenAI tool-calling protocol let the
 * chat drive the harness itself (search papers, index arXiv). Models that
 * don't (Interfaze) get relevant papers pre-fetched into their context
 * instead, so they still answer grounded in the library.
 */

export interface ChatModel {
  id: string
  label: string
  hint: string
  provider: 'openrouter' | 'interfaze'
  supportsTools: boolean
}

export const CHAT_MODELS: ChatModel[] = [
  {
    id: 'nvidia/nemotron-3-ultra-550b-a55b:free',
    label: 'Nemotron 3 Ultra',
    hint: 'free · tools · thorough',
    provider: 'openrouter',
    supportsTools: true,
  },
  {
    id: 'openrouter/free',
    label: 'Auto (free)',
    hint: 'free · routes to a free model',
    provider: 'openrouter',
    supportsTools: false,
  },
  {
    id: 'tencent/hy3:free',
    label: 'Hunyuan 3',
    hint: 'free · papers pre-fetched',
    provider: 'openrouter',
    supportsTools: false,
  },
  // Interfaze is wired and ready (provider: 'interfaze', INTERFAZE_API_KEY in
  // .env.local) but its key currently returns "no credits left"
  // (insufficient_quota), so it is kept out of the picker rather than shipping
  // an option that always errors. Add credits, then uncomment:
  // {
  //   id: 'interfaze-beta',
  //   label: 'Interfaze',
  //   hint: 'no tools · papers pre-fetched',
  //   provider: 'interfaze',
  //   supportsTools: false,
  // },
]

export const DEFAULT_MODEL_ID = CHAT_MODELS[0].id

export function getModel(id?: string | null): ChatModel {
  return CHAT_MODELS.find((m) => m.id === id) ?? CHAT_MODELS[0]
}
