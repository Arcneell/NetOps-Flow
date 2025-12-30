/**
 * Zod validation schemas for form validation.
 * Provides type-safe validation with detailed error messages.
 */
import { z } from 'zod'

// ==================== FILE VALIDATION ====================

/**
 * Avatar file validation schema.
 * Validates file type, size, and basic properties.
 */
export const avatarFileSchema = z.object({
  name: z.string().min(1, 'File name is required'),
  size: z
    .number()
    .max(2 * 1024 * 1024, 'File size must be less than 2MB'),
  type: z
    .string()
    .refine(
      (type) => ['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(type),
      'File must be a valid image (JPEG, PNG, GIF, or WebP)'
    )
})

/**
 * Validate a File object for avatar upload.
 * @param {File} file - The file to validate
 * @returns {{ success: boolean, error?: string, data?: object }}
 */
export function validateAvatarFile(file) {
  if (!file) {
    return { success: false, error: 'No file provided' }
  }

  const result = avatarFileSchema.safeParse({
    name: file.name,
    size: file.size,
    type: file.type
  })

  if (!result.success) {
    const firstError = result.error.errors[0]
    return { success: false, error: firstError.message }
  }

  return { success: true, data: result.data }
}

// ==================== SCRIPT FILE VALIDATION ====================

/**
 * Script file validation schema.
 * Validates script files for upload.
 */
export const scriptFileSchema = z.object({
  name: z.string().min(1, 'File name is required'),
  size: z
    .number()
    .max(10 * 1024 * 1024, 'Script file must be less than 10MB'),
  type: z
    .string()
    .optional()
    .refine(
      (type) => {
        if (!type) return true // Allow empty type for some scripts
        const allowedTypes = [
          'text/x-python',
          'text/x-python-script',
          'application/x-python-code',
          'text/x-sh',
          'application/x-sh',
          'text/plain',
          'application/octet-stream'
        ]
        return allowedTypes.includes(type)
      },
      'Invalid script file type'
    ),
  extension: z
    .string()
    .refine(
      (ext) => ['.py', '.sh', '.bash', '.ps1'].includes(ext.toLowerCase()),
      'Script must be Python (.py), Bash (.sh), or PowerShell (.ps1)'
    )
})

/**
 * Validate a File object for script upload.
 * @param {File} file - The file to validate
 * @returns {{ success: boolean, error?: string, data?: object }}
 */
export function validateScriptFile(file) {
  if (!file) {
    return { success: false, error: 'No file provided' }
  }

  const extension = file.name.includes('.')
    ? '.' + file.name.split('.').pop().toLowerCase()
    : ''

  const result = scriptFileSchema.safeParse({
    name: file.name,
    size: file.size,
    type: file.type,
    extension
  })

  if (!result.success) {
    const firstError = result.error.errors[0]
    return { success: false, error: firstError.message }
  }

  return { success: true, data: result.data }
}

// ==================== ATTACHMENT VALIDATION ====================

/**
 * Attachment file validation schema.
 * Validates generic attachment files.
 */
export const attachmentFileSchema = z.object({
  name: z.string().min(1, 'File name is required'),
  size: z
    .number()
    .max(50 * 1024 * 1024, 'File must be less than 50MB')
})

/**
 * Validate a File object for attachment upload.
 * @param {File} file - The file to validate
 * @param {number} maxSizeMB - Maximum file size in MB (default: 50)
 * @returns {{ success: boolean, error?: string, data?: object }}
 */
export function validateAttachmentFile(file, maxSizeMB = 50) {
  if (!file) {
    return { success: false, error: 'No file provided' }
  }

  const schema = z.object({
    name: z.string().min(1, 'File name is required'),
    size: z.number().max(maxSizeMB * 1024 * 1024, `File must be less than ${maxSizeMB}MB`)
  })

  const result = schema.safeParse({
    name: file.name,
    size: file.size
  })

  if (!result.success) {
    const firstError = result.error.errors[0]
    return { success: false, error: firstError.message }
  }

  return { success: true, data: result.data }
}

// ==================== FORM FIELD VALIDATION ====================

/**
 * Password validation schema.
 * Minimum 8 characters requirement.
 */
export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')

/**
 * Email validation schema.
 */
export const emailSchema = z
  .string()
  .email('Invalid email address')
  .optional()
  .or(z.literal(''))

/**
 * Username validation schema.
 */
export const usernameSchema = z
  .string()
  .min(3, 'Username must be at least 3 characters')
  .max(50, 'Username must be less than 50 characters')
  .regex(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, underscores, and hyphens')

/**
 * MFA code validation schema.
 */
export const mfaCodeSchema = z
  .string()
  .length(6, 'MFA code must be exactly 6 digits')
  .regex(/^\d{6}$/, 'MFA code must contain only digits')

/**
 * Validate a password.
 * @param {string} password - The password to validate
 * @returns {{ success: boolean, error?: string }}
 */
export function validatePassword(password) {
  const result = passwordSchema.safeParse(password)
  if (!result.success) {
    return { success: false, error: result.error.errors[0].message }
  }
  return { success: true }
}

/**
 * Validate an email address.
 * @param {string} email - The email to validate
 * @returns {{ success: boolean, error?: string }}
 */
export function validateEmail(email) {
  const result = emailSchema.safeParse(email)
  if (!result.success) {
    return { success: false, error: result.error.errors[0].message }
  }
  return { success: true }
}

/**
 * Validate an MFA code.
 * @param {string} code - The MFA code to validate
 * @returns {{ success: boolean, error?: string }}
 */
export function validateMfaCode(code) {
  const result = mfaCodeSchema.safeParse(code)
  if (!result.success) {
    return { success: false, error: result.error.errors[0].message }
  }
  return { success: true }
}
