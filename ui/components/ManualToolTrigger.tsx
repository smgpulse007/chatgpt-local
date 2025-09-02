'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Globe, Search } from 'lucide-react';

interface ManualToolTriggerProps {
  onTriggerSearch: (query: string) => void;
  disabled?: boolean;
}

export default function ManualToolTrigger({ onTriggerSearch, disabled }: ManualToolTriggerProps) {
  const handleTriggerSearch = () => {
    const query = prompt("Enter search query:");
    if (query && query.trim()) {
      onTriggerSearch(query.trim());
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2 p-3 mx-4 mb-4 rounded-2xl glass border border-border/50"
    >
      <div className="flex items-center gap-2 text-sm text-white/70">
        <Globe size={16} className="text-orange-400" />
        <span>Assistant didn't use web search?</span>
      </div>
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={handleTriggerSearch}
        disabled={disabled}
        className="btn-glass px-3 py-1.5 rounded-xl text-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Search size={14} />
        Try browsing anyway
      </motion.button>
    </motion.div>
  );
}
