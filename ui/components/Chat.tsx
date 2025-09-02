'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Message as MessageType, ChatRequest, chatAPI, ConversationInfo, ModelInfo } from '@/lib/api';
import Message from './Message';
import Sidebar from './Sidebar';
import { Button } from './ui/button';
import { 
  Send, 
  Square, 
  Menu, 
  Sparkles, 
  Globe, 
  Thermometer,
  Cpu,
  MessageSquare,
  Settings
} from 'lucide-react';

interface ChatState {
  messages: MessageType[];
  isStreaming: boolean;
  currentResponse: string;
  conversations: ConversationInfo[];
  currentConversationId?: string;
  models: ModelInfo[];
  selectedModel: string;
  enableBrowsing: boolean;
  temperature: number;
  sidebarOpen: boolean;
}

export default function Chat() {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isStreaming: false,
    currentResponse: '',
    conversations: [],
    models: [],
    selectedModel: 'gpt-oss:20b',
    enableBrowsing: true, // Default to enabled for better UX
    temperature: 0.7,
    sidebarOpen: true,
  });

  const [input, setInput] = useState('');
  const [toolCalls, setToolCalls] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadInitialData();
    
    // Load browsing preference from localStorage
    const savedBrowsing = localStorage.getItem('enableBrowsing');
    if (savedBrowsing !== null) {
      setState(prev => ({ 
        ...prev, 
        enableBrowsing: JSON.parse(savedBrowsing) 
      }));
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [state.messages, state.currentResponse]);

  const loadInitialData = async () => {
    try {
      const [models, conversations] = await Promise.all([
        chatAPI.getModels(),
        chatAPI.getConversations(),
      ]);
      
      setState(prev => ({
        ...prev,
        models,
        conversations,
        selectedModel: models.find(m => m.name.includes('gpt-oss')) ? 
          models.find(m => m.name.includes('gpt-oss'))!.name : 
          models[0]?.name || 'gpt-oss:20b'
      }));
    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    if (!input.trim() || state.isStreaming) return;

    const userMessage: MessageType = {
      role: 'user',
      content: input.trim(),
    };

    const newMessages = [...state.messages, userMessage];
    setState(prev => ({
      ...prev,
      messages: newMessages,
      isStreaming: true,
      currentResponse: '',
    }));

    setInput('');
    setToolCalls([]);

    const request: ChatRequest = {
      messages: newMessages,
      conversation_id: state.currentConversationId,
      enable_browsing: state.enableBrowsing,
      temperature: state.temperature,
      model: state.selectedModel,
    };

    try {
      let assistantResponse = '';
      const currentToolCalls: any[] = [];

      for await (const chunk of chatAPI.streamChat(request)) {
        if (chunk.type === 'token') {
          assistantResponse += chunk.content || '';
          setState(prev => ({
            ...prev,
            currentResponse: assistantResponse,
          }));
        } else if (chunk.type === 'tool_call') {
          currentToolCalls.push({
            type: 'call',
            tool_name: chunk.tool_name,
            arguments: chunk.arguments,
          });
          setToolCalls([...currentToolCalls]);
        } else if (chunk.type === 'tool_result') {
          currentToolCalls.push({
            type: 'result',
            tool_name: chunk.tool_name,
            result: chunk.result,
          });
          setToolCalls([...currentToolCalls]);
        } else if (chunk.type === 'error') {
          console.error('Chat error:', chunk.content);
          assistantResponse += `\n\nError: ${chunk.content}`;
          setState(prev => ({
            ...prev,
            currentResponse: assistantResponse,
          }));
          break;
        } else if (chunk.type === 'done') {
          break;
        }
      }

      // Add final assistant message
      const assistantMessage: MessageType = {
        role: 'assistant',
        content: assistantResponse,
      };

      setState(prev => ({
        ...prev,
        messages: [...newMessages, assistantMessage],
        isStreaming: false,
        currentResponse: '',
      }));

      // Refresh conversations list
      const conversations = await chatAPI.getConversations();
      setState(prev => ({
        ...prev,
        conversations,
        currentConversationId: conversations[0]?.id || prev.currentConversationId,
      }));

    } catch (error) {
      console.error('Failed to send message:', error);
      setState(prev => ({
        ...prev,
        isStreaming: false,
        currentResponse: '',
      }));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleNewConversation = () => {
    setState(prev => ({
      ...prev,
      messages: [],
      currentConversationId: undefined,
      currentResponse: '',
    }));
    setToolCalls([]);
  };

  const handleSelectConversation = async (conversationId: string) => {
    try {
      const messages = await chatAPI.getConversationMessages(conversationId);
      setState(prev => ({
        ...prev,
        messages,
        currentConversationId: conversationId,
        currentResponse: '',
      }));
      setToolCalls([]);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await chatAPI.deleteConversation(conversationId);
      const conversations = await chatAPI.getConversations();
      setState(prev => ({
        ...prev,
        conversations,
        currentConversationId: prev.currentConversationId === conversationId ? 
          undefined : prev.currentConversationId,
        messages: prev.currentConversationId === conversationId ? [] : prev.messages,
      }));
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Sidebar */}
      <AnimatePresence>
        {state.sidebarOpen && (
          <motion.div
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="w-80 h-full"
          >
            <Sidebar
              conversations={state.conversations}
              currentConversationId={state.currentConversationId}
              onNewConversation={handleNewConversation}
              onSelectConversation={handleSelectConversation}
              onDeleteConversation={handleDeleteConversation}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col backdrop-blur-sm">
        {/* Header */}
        <div className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700/50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setState(prev => ({ ...prev, sidebarOpen: !prev.sidebarOpen }))}
                className="hover:bg-gray-700/50"
              >
                <Menu size={20} />
              </Button>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Sparkles size={16} className="text-white" />
                </div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  Local ChatGPT
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Model Selector */}
              <div className="flex items-center gap-2">
                <Cpu size={16} className="text-gray-400" />
                <select
                  value={state.selectedModel}
                  onChange={(e) => setState(prev => ({ ...prev, selectedModel: e.target.value }))}
                  className="bg-gray-700/50 backdrop-blur-md border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {state.models.map((model) => (
                    <option key={model.name} value={model.name} className="bg-gray-800">
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Browsing Toggle */}
              <div className="flex items-center gap-2">
                <Globe size={16} className={state.enableBrowsing ? "text-green-400" : "text-gray-400"} />
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={state.enableBrowsing}
                    onChange={(e) => {
                      const newBrowsing = e.target.checked;
                      setState(prev => ({ ...prev, enableBrowsing: newBrowsing }));
                      localStorage.setItem('enableBrowsing', JSON.stringify(newBrowsing));
                    }}
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <span className={state.enableBrowsing ? "text-green-400" : "text-gray-300"}>
                    Browsing
                  </span>
                </label>
              </div>

              {/* Temperature Slider */}
              <div className="flex items-center gap-2">
                <Thermometer size={16} className="text-gray-400" />
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={state.temperature}
                  onChange={(e) => setState(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  className="w-20 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                />
                <span className="text-xs text-gray-400 w-8">{state.temperature}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {state.messages.length === 0 && !state.isStreaming && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center h-full text-center"
            >
              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-6">
                <MessageSquare size={32} className="text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-100 mb-2">Welcome to Local ChatGPT</h2>
              <p className="text-gray-400 max-w-md">
                Ask me anything! I can help with information, analysis, coding, and when browsing is enabled, 
                I can search the web for the latest information.
              </p>
            </motion.div>
          )}

          <AnimatePresence>
            {state.messages.map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <Message message={message} />
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Tool calls */}
          <AnimatePresence>
            {toolCalls.length > 0 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 backdrop-blur-sm border border-blue-500/20 rounded-xl p-4"
              >
                <h4 className="font-semibold mb-3 text-blue-400 flex items-center gap-2">
                  <Settings size={16} />
                  Agent Actions
                </h4>
                <div className="space-y-2">
                  {toolCalls.map((call, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="text-sm"
                    >
                      {call.type === 'call' && (
                        <div className="text-blue-300 flex items-center gap-2">
                          <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                          🔧 {call.tool_name}({JSON.stringify(call.arguments)})
                        </div>
                      )}
                      {call.type === 'result' && (
                        <div className="text-green-300 ml-4 flex items-center gap-2">
                          <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                          ✓ Result: {JSON.stringify(call.result, null, 2).slice(0, 200)}...
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Current streaming response */}
          {state.isStreaming && state.currentResponse && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Message
                message={{
                  role: 'assistant',
                  content: state.currentResponse,
                }}
                isStreaming={true}
              />
            </motion.div>
          )}

          {/* Typing indicator */}
          {state.isStreaming && !state.currentResponse && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3 text-gray-400"
            >
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-75"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-150"></div>
              </div>
              <span>Assistant is thinking...</span>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-gray-800/50 backdrop-blur-md border-t border-gray-700/50 p-4">
          <div className="flex gap-3 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message... (Shift+Enter for new line)"
                className="w-full resize-none bg-gray-700/50 backdrop-blur-md border border-gray-600/50 rounded-xl px-4 py-3 text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                rows={Math.min(input.split('\n').length, 4)}
                disabled={state.isStreaming}
              />
            </div>
            
            {state.isStreaming ? (
              <Button
                variant="destructive"
                size="icon"
                onClick={() => setState(prev => ({ ...prev, isStreaming: false }))}
                className="self-end rounded-xl w-12 h-12"
              >
                <Square size={20} />
              </Button>
            ) : (
              <Button
                onClick={handleSendMessage}
                disabled={!input.trim()}
                size="icon"
                className="self-end rounded-xl w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
              >
                <Send size={20} />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
