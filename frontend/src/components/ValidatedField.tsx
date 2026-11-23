import { useId, useState, type FormEvent, type ReactNode } from 'react'

interface ValidationProps {
  'aria-invalid': boolean | undefined
  'aria-describedby': string | undefined
}

interface ValidatedFieldProps {
  label: string
  value: string
  children: (props: ValidationProps) => ReactNode
}

export default function ValidatedField({ label, value, children }: ValidatedFieldProps) {
  const messageId = useId()
  const [error, setError] = useState<{ value: string, message: string } | null>(null)
  const message = error?.value === value ? error.message : null

  function onInvalid(event: FormEvent<HTMLLabelElement>): void {
    const field = event.target
    if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement)) return
    setError({ value: field.value, message: field.validationMessage })
  }

  function onInput(event: FormEvent<HTMLLabelElement>): void {
    if (error === null) return
    const field = event.target
    if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement)) return
    setError(field.validity.valid ? null : {
      value: field.value,
      message: field.validationMessage
    })
  }

  return (
    <label onInvalid={onInvalid} onInput={onInput}>
      {label}
      {children({
        'aria-invalid': message !== null ? true : undefined,
        'aria-describedby': message !== null ? messageId : undefined
      })}
      {message !== null && <span id={messageId} className="field-error" role="alert">{message}</span>}
    </label>
  )
}
