import type { SelectOption } from '../options';

interface BaseProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}

/**
 * Campos do formulario de edicao. Sao tres blocos identicos nos tres papeis;
 * concentra-los aqui evita reescrever label + input a cada campo.
 */
export function TextField({
  id,
  label,
  value,
  onChange,
  maxLength,
  placeholder,
  type = 'text',
}: BaseProps & { maxLength?: number; placeholder?: string; type?: string }) {
  return (
    <div className="form-field">
      <label className="form-label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="form-input"
        type={type}
        value={value}
        maxLength={maxLength}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

export function TextAreaField({
  id,
  label,
  value,
  onChange,
  rows = 4,
  hint,
}: BaseProps & { rows?: number; hint?: string }) {
  return (
    <div className="form-field form-field-wide">
      <label className="form-label" htmlFor={id}>
        {label}
      </label>
      <textarea
        id={id}
        className="form-input form-textarea"
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {hint && <p className="form-hint">{hint}</p>}
    </div>
  );
}

export function SelectField({
  id,
  label,
  value,
  onChange,
  options,
  emptyLabel = 'Não informado',
  allowEmpty = true,
}: BaseProps & {
  options: SelectOption[];
  emptyLabel?: string;
  /** `false` para campo que a API nao aceita nulo, como o status do atleta. */
  allowEmpty?: boolean;
}) {
  return (
    <div className="form-field">
      <label className="form-label" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className="form-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {allowEmpty && <option value="">{emptyLabel}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
