export interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  name?: string;
  tool_call_id?: string;
}

export interface ChatRequest {
  messages: Message[];
  conversation_id?: string;
  enable_browsing?: boolean;
  system?: string;
  temperature?: number;
  model?: string;
  max_tokens?: number;
}

export interface StreamChunk {
  type: 'token' | 'tool_call' | 'tool_result' | 'error' | 'done';
  content?: string;
  tool_name?: string;
  arguments?: Record<string, any>;
  result?: Record<string, any>;
}

export interface ConversationInfo {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ModelInfo {
  name: string;
  size: number;
  modified_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export class ChatAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async getModels(): Promise<ModelInfo[]> {
    const response = await fetch(`${this.baseUrl}/models`);
    if (!response.ok) {
      throw new Error(`Failed to fetch models: ${response.statusText}`);
    }
    return response.json();
  }

  async getConversations(): Promise<ConversationInfo[]> {
    const response = await fetch(`${this.baseUrl}/conversations`);
    if (!response.ok) {
      throw new Error(`Failed to fetch conversations: ${response.statusText}`);
    }
    return response.json();
  }

  async getConversationMessages(conversationId: string): Promise<Message[]> {
    const response = await fetch(`${this.baseUrl}/conversations/${conversationId}/messages`);
    if (!response.ok) {
      throw new Error(`Failed to fetch messages: ${response.statusText}`);
    }
    return response.json();
  }

  async deleteConversation(conversationId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete conversation: ${response.statusText}`);
    }
  }

  async *streamChat(request: ChatRequest): AsyncGenerator<StreamChunk, void, unknown> {
    try {
      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data.trim()) {
                try {
                  const chunk: StreamChunk = JSON.parse(data);
                  yield chunk;
                  
                  if (chunk.type === 'done' || chunk.type === 'error') {
                    return;
                  }
                } catch (e) {
                  console.warn('Failed to parse SSE data:', data);
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error('Stream chat error:', error);
      yield {
        type: 'error',
        content: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/healthz`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const chatAPI = new ChatAPI();
