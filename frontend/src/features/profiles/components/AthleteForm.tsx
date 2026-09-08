import { useState } from 'react';
import type { ReactNode } from 'react';
import { buildAthletePayload } from '../editForm';
import type { AthleteFormValues } from '../editForm';
import { FOOT_OPTIONS, POSITION_OPTIONS, STATUS_OPTIONS } from '../options';
import { SelectField, TextAreaField, TextField } from './FormFields';

interface Props {
  initial: AthleteFormValues;
  onSave: (changes: Record<string, unknown>) => void;
  isSaving: boolean;
  status: ReactNode;
}

export function AthleteForm({ initial, onSave, isSaving, status }: Props) {
  const [values, setValues] = useState<AthleteFormValues>(initial);

  function set(key: keyof AthleteFormValues, value: string) {
    setValues((atual) => ({ ...atual, [key]: value }));
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    // So o que mudou: o update e parcial e reenviar o resto sobrescreveria
    // valores identicos sem necessidade.
    onSave(buildAthletePayload(initial, values));
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <SelectField
          id="position"
          label="Posição"
          value={values.position}
          onChange={(value) => set('position', value)}
          options={POSITION_OPTIONS}
        />

        <TextField
          id="birth_date"
          label="Data de nascimento"
          type="date"
          value={values.birth_date}
          onChange={(value) => set('birth_date', value)}
        />

        <TextField
          id="height_cm"
          label="Altura (cm)"
          type="number"
          placeholder="178"
          value={values.height_cm}
          onChange={(value) => set('height_cm', value)}
        />

        <SelectField
          id="dominant_foot"
          label="Pé dominante"
          value={values.dominant_foot}
          onChange={(value) => set('dominant_foot', value)}
          options={FOOT_OPTIONS}
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

        <TextField
          id="current_club"
          label="Clube atual"
          value={values.current_club}
          onChange={(value) => set('current_club', value)}
        />

        <SelectField
          id="status"
          label="Situação"
          value={values.status}
          onChange={(value) => set('status', value)}
          options={STATUS_OPTIONS}
          allowEmpty={false}
        />

        <TextAreaField
          id="club_history"
          label="Histórico de clubes"
          value={values.club_history}
          onChange={(value) => set('club_history', value)}
          hint="Texto livre: um clube por linha, com o período em que você jogou."
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
