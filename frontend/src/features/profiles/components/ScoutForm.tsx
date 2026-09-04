import { useState } from 'react';
import type { ReactNode } from 'react';
import { buildScoutPayload } from '../editForm';
import type { ScoutFormValues } from '../editForm';
import { TextAreaField, TextField } from './FormFields';

interface Props {
  initial: ScoutFormValues;
  onSave: (changes: Record<string, unknown>) => void;
  isSaving: boolean;
  status: ReactNode;
}

export function ScoutForm({ initial, onSave, isSaving, status }: Props) {
  const [values, setValues] = useState<ScoutFormValues>(initial);

  function set(key: keyof ScoutFormValues, value: string) {
    setValues((atual) => ({ ...atual, [key]: value }));
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    onSave(buildScoutPayload(initial, values));
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <TextField
          id="organization"
          label="Organização"
          value={values.organization}
          onChange={(value) => set('organization', value)}
        />

        <TextField
          id="credential"
          label="Credencial"
          value={values.credential}
          onChange={(value) => set('credential', value)}
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
