import { useState } from 'react';
import type { ReactNode } from 'react';
import { buildClubPayload } from '../editForm';
import type { ClubFormValues } from '../editForm';
import { CATEGORY_OPTIONS } from '../options';
import { TextAreaField, TextField } from './FormFields';

interface Props {
  initial: ClubFormValues;
  onSave: (changes: Record<string, unknown>) => void;
  isSaving: boolean;
  status: ReactNode;
}

export function ClubForm({ initial, onSave, isSaving, status }: Props) {
  const [values, setValues] = useState<ClubFormValues>(initial);

  function set(key: 'legal_name' | 'cnpj' | 'city' | 'state' | 'bio', value: string) {
    setValues((atual) => ({ ...atual, [key]: value }));
  }

  function toggleCategory(category: string) {
    setValues((atual) => ({
      ...atual,
      // A API substitui a lista inteira; aqui so montamos a lista final.
      categories: atual.categories.includes(category)
        ? atual.categories.filter((item) => item !== category)
        : [...atual.categories, category],
    }));
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSave(buildClubPayload(initial, values));
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <TextField
          id="legal_name"
          label="Razão social"
          value={values.legal_name}
          onChange={(value) => set('legal_name', value)}
        />

        <TextField
          id="cnpj"
          label="CNPJ"
          placeholder="00000000000000"
          value={values.cnpj}
          onChange={(value) => set('cnpj', value)}
        />

        <TextField
          id="city"
          label="Cidade"
          value={values.city}
          onChange={(value) => set('city', value)}
        />

        <TextField
          id="state"
          label="Estado (UF)"
          maxLength={2}
          placeholder="SP"
          value={values.state}
          onChange={(value) => set('state', value)}
        />

        <fieldset className="form-field form-field-wide form-fieldset">
          <legend className="form-label">Categorias</legend>
          <div className="form-checkboxes">
            {CATEGORY_OPTIONS.map((option) => (
              <label className="form-checkbox" key={option.value}>
                <input
                  type="checkbox"
                  checked={values.categories.includes(option.value)}
                  onChange={() => toggleCategory(option.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <TextAreaField
          id="bio"
          label="Bio"
          value={values.bio}
          onChange={(value) => set('bio', value)}
        />
      </div>

      <div className="form-actions">
        <button type="submit" className="btn-primary" disabled={isSaving}>
          {isSaving ? 'Salvando...' : 'Salvar alterações'}
        </button>
        {status}
      </div>
    </form>
  );
}
