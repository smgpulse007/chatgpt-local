'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion } from 'framer-motion';
import { Copy, User, Bot, Sparkles, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { Message as MessageType } from '@/lib/api';

interface MessageProps {
  message: MessageType;
  isStreaming?: boolean;
}

export default function Message({ message, isStreaming = false }: MessageProps) {
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'user':
        return <User size={16} className="text-white" />;
      case 'assistant':
        return <Bot size={16} className="text-white" />;
      case 'system':
        return <Sparkles size={16} className="text-white" />;
      default:
        return <Bot size={16} className="text-white" />;
    }
  };

  const getRoleName = (role: string) => {
    switch (role) {
      case 'user':
        return 'You';
      case 'assistant':
        return 'Assistant';
      case 'system':
        return 'System';
      default:
        return role;
    }
  };

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'} max-w-none group`}
    >
      {/* Avatar for assistant */}
      {isAssistant && (
        <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
          {getRoleIcon(message.role)}
        </div>
      )}

      {/* Message content */}
      <div
        className={`
          max-w-[85%] relative
          ${isUser
            ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-2xl rounded-br-md shadow-lg'
            : 'bg-gray-800/50 backdrop-blur-sm border border-gray-700/30 text-gray-100 rounded-2xl rounded-bl-md shadow-lg'
          }
          px-6 py-4
        `}
      >
        {/* Message header */}
        <div className="flex items-center gap-2 mb-3 text-sm">
          {getRoleIcon(message.role)}
          <span className={`font-medium ${isUser ? 'text-blue-100' : 'text-gray-300'}`}>
            {getRoleName(message.role)}
          </span>
          {isStreaming && isAssistant && (
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="flex items-center gap-1 text-blue-300"
            >
              <Clock size={12} />
              <span className="text-xs">Thinking...</span>
            </motion.div>
          )}
        </div>

        {/* Message content */}
        <div className={`prose max-w-none ${isUser ? 'prose-invert' : 'prose-gray dark:prose-invert'}`}>
          {isUser ? (
            <div className="whitespace-pre-wrap text-white">{message.content}</div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <pre className="bg-gray-900/50 border border-gray-600/30 p-4 rounded-lg overflow-x-auto my-3">
                      <code className={`${className} text-gray-100 text-sm font-mono`} {...props}>
                        {children}
                      </code>
                    </pre>
                  ) : (
                    <code className="bg-gray-700/50 border border-gray-600/30 px-2 py-1 rounded text-sm font-mono text-blue-300" {...props}>
                      {children}
                    </code>
                  );
                },
                a({ children, href, ...props }: any) {
                  return (
                    <a 
                      href={href} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="text-blue-400 hover:text-blue-300 underline transition-colors"
                      {...props}
                    >
                      {children}
                    </a>
                  );
                },
                p({ children }: any) {
                  return <p className="mb-3 last:mb-0 leading-relaxed text-gray-100">{children}</p>;
                },
                ul({ children }: any) {
                  return <ul className="list-disc pl-6 mb-3 space-y-1 text-gray-100">{children}</ul>;
                },
                ol({ children }: any) {
                  return <ol className="list-decimal pl-6 mb-3 space-y-1 text-gray-100">{children}</ol>;
                },
                li({ children }: any) {
                  return <li className="text-gray-100">{children}</li>;
                },
                blockquote({ children }: any) {
                  return (
                    <blockquote className="border-l-4 border-blue-500/50 pl-4 italic bg-gray-700/30 rounded-r-lg py-2 my-3 text-gray-200">
                      {children}
                    </blockquote>
                  );
                },
                h1({ children }: any) {
                  return <h1 className="text-2xl font-bold mb-3 text-gray-100">{children}</h1>;
                },
                h2({ children }: any) {
                  return <h2 className="text-xl font-bold mb-3 text-gray-100">{children}</h2>;
                },
                h3({ children }: any) {
                  return <h3 className="text-lg font-semibold mb-2 text-gray-100">{children}</h3>;
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Streaming indicator */}
        {isStreaming && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-3 flex items-center gap-2"
          >
            <motion.span
              animate={{ opacity: [0, 1, 0] }}
              transition={{ duration: 0.8, repeat: Infinity }}
              className="inline-block w-2 h-5 bg-blue-400 rounded"
            />
          </motion.div>
        )}

        {/* Message timestamp */}
        <div
          className={`
            text-xs mt-3 opacity-60
            ${isUser ? 'text-blue-100' : 'text-gray-400'}
          `}
        >
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>

        {/* Copy button */}
        <Button
          variant="ghost"
          size="icon"
          className={`
            absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-all duration-200 h-8 w-8
            ${isUser ? 'hover:bg-blue-500/20 text-blue-100' : 'hover:bg-gray-600/50 text-gray-300'}
          `}
          onClick={() => copyToClipboard(message.content)}
        >
          <Copy size={14} />
        </Button>
      </div>

      {/* Avatar for user */}
      {isUser && (
        <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center shadow-lg">
          {getRoleIcon(message.role)}
        </div>
      )}
    </motion.div>
  );
}
