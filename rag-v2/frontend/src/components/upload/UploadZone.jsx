import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react'
import clsx from 'clsx'

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/webp': ['.webp'],
}

export function UploadZone({ onUpload, uploadQueue = [], compact = false }) {
  const onDrop = useCallback((accepted) => { if (accepted.length) onUpload(accepted) }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 10,
    maxSize: 50 * 1024 * 1024,
  })

  return (
    <div className="space-y-2">
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200 text-center',
          compact ? 'p-4' : 'p-8',
          isDragActive
            ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20 scale-[1.01]'
            : 'border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-600 hover:bg-slate-50 dark:hover:bg-slate-800/50'
        )}
      >
        <input {...getInputProps()} />
        <motion.div animate={isDragActive ? { scale: 1.05 } : { scale: 1 }} className="flex flex-col items-center gap-2">
          <div className={clsx(
            'rounded-xl flex items-center justify-center transition-colors',
            compact ? 'w-8 h-8' : 'w-12 h-12',
            isDragActive ? 'bg-brand-100 dark:bg-brand-800 text-brand-600' : 'bg-slate-100 dark:bg-slate-700 text-slate-500'
          )}>
            <Upload size={compact ? 16 : 22} />
          </div>
          <div>
            <p className={clsx('font-medium text-slate-700 dark:text-slate-300', compact ? 'text-xs' : 'text-sm')}>
              {isDragActive ? 'Drop to upload' : compact ? 'Drop files or click' : 'Drag & drop files here'}
            </p>
            {!compact && (
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">PDF, DOCX, TXT, PNG, JPG · max 50 MB</p>
            )}
          </div>
          {!compact && (
            <span className="text-xs text-brand-600 dark:text-brand-400 font-medium">Browse files</span>
          )}
        </motion.div>
      </div>

      {/* Upload queue */}
      <AnimatePresence>
        {uploadQueue.map(item => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="card p-2.5 space-y-1.5"
          >
            <div className="flex items-center gap-2">
              {item.status === 'done'
                ? <CheckCircle2 size={13} className="text-green-500 flex-shrink-0" />
                : item.status === 'error'
                ? <AlertCircle size={13} className="text-red-500 flex-shrink-0" />
                : <Loader2 size={13} className="text-brand-500 animate-spin flex-shrink-0" />
              }
              <span className="text-xs text-slate-700 dark:text-slate-300 truncate flex-1">{item.name}</span>
              <span className="text-xs text-slate-400 font-mono">{item.progress}%</span>
            </div>
            {item.status === 'uploading' && (
              <div className="h-1 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${item.progress}%` }}
                  className="h-full bg-gradient-to-r from-brand-400 to-indigo-500 rounded-full"
                />
              </div>
            )}
            {item.status === 'error' && (
              <p className="text-xs text-red-500">{item.error}</p>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
