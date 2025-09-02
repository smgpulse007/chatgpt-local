'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ConversationInfo } from '@/lib/api';
import { Button } from './ui/button';
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Search,
  Settings,
  User,
  Sparkles,
  Clock,
  Archive
} from 'lucide-react';

interface SidebarProps {
  conversations: ConversationInfo[];
  currentConversationId?: string;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const truncateTitle = (title: string, maxLength: number = 30) => {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
  };

  return (
    <div className="w-full h-full bg-gray-900/50 backdrop-blur-md border-r border-gray-700/50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700/50">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Sparkles size={16} className="text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-100">Conversations</h2>
            <p className="text-xs text-gray-400">{conversations.length} total</p>
          </div>
        </div>

        {/* New Chat Button */}
        <Button
          onClick={onNewConversation}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white border-0 shadow-lg"
          variant="default"
        >
          <Plus size={16} className="mr-2" />
          New Chat
        </Button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-gray-700/50">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-600/50 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence>
          {filteredConversations.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center p-8 text-center"
            >
              <MessageSquare size={48} className="text-gray-600 mb-4" />
              <p className="text-gray-400 text-sm">
                {searchQuery ? 'No conversations found' : 'No conversations yet'}
              </p>
              <p className="text-gray-500 text-xs mt-1">
                {searchQuery ? 'Try a different search term' : 'Start a new chat to begin'}
              </p>
            </motion.div>
          ) : (
            <div className="p-2 space-y-1">
              {filteredConversations.map((conversation, index) => (
                <motion.div
                  key={conversation.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`
                    group relative cursor-pointer rounded-xl p-3 transition-all duration-200
                    ${currentConversationId === conversation.id
                      ? 'bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/30 shadow-lg'
                      : 'hover:bg-gray-800/50 border border-transparent'
                    }
                  `}
                  onClick={() => onSelectConversation(conversation.id)}
                >
                  <div className="flex items-start gap-3">
                    <div className={`
                      w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                      ${currentConversationId === conversation.id
                        ? 'bg-gradient-to-r from-blue-500 to-purple-600'
                        : 'bg-gray-700/50'
                      }
                    `}>
                      <MessageSquare size={14} className="text-white" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h3 className={`
                        font-medium text-sm truncate
                        ${currentConversationId === conversation.id
                          ? 'text-white'
                          : 'text-gray-200 group-hover:text-white'
                        }
                      `}>
                        {truncateTitle(conversation.title)}
                      </h3>
                      
                      <div className="flex items-center gap-2 mt-1">
                        <Clock size={10} className="text-gray-500" />
                        <span className="text-xs text-gray-500">
                          {formatDate(conversation.updated_at)}
                        </span>
                      </div>
                      
                      {conversation.message_count && (
                        <div className="flex items-center gap-1 mt-1">
                          <div className="w-1 h-1 bg-gray-500 rounded-full"></div>
                          <span className="text-xs text-gray-500">
                            {conversation.message_count} messages
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Delete Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 hover:bg-red-500/20 hover:text-red-400"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conversation.id);
                    }}
                  >
                    <Trash2 size={12} />
                  </Button>
                </motion.div>
              ))}
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center">
              <User size={12} className="text-white" />
            </div>
            <span className="text-sm text-gray-300">User</span>
          </div>
          
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowSettings(!showSettings)}
            className="hover:bg-gray-700/50 text-gray-400 hover:text-white"
          >
            <Settings size={16} />
          </Button>
        </div>

        {/* Settings Panel */}
        <AnimatePresence>
          {showSettings && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 p-3 bg-gray-800/50 rounded-lg border border-gray-600/30"
            >
              <div className="space-y-2">
                <button className="w-full text-left text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2">
                  <Archive size={14} />
                  Export Conversations
                </button>
                <button className="w-full text-left text-sm text-gray-300 hover:text-white transition-colors flex items-center gap-2">
                  <Settings size={14} />
                  Preferences
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-4 text-xs text-gray-500 text-center">
          <p>Local ChatGPT</p>
          <p>Powered by Ollama</p>
        </div>
      </div>
    </div>
  );
}
