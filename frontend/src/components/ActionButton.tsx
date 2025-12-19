// ABOUTME: Action button component that handles backend and client-side actions.
// ABOUTME: Routes add_to_bundle to client-side store, others to backend via sendMessage.

import { useBundleStore } from '../stores/bundleStore';
import { useChatInteract } from '@chainlit/react-client';
import type { IAction } from '@chainlit/react-client';
import type { ActionPayload } from '../types';

interface Props {
  action: IAction;
}

export function ActionButton({ action }: Props) {
  const { addItem, hasItem } = useBundleStore();
  const { sendMessage } = useChatInteract();

  const handleClick = async () => {
    const payload = (action.payload || {}) as ActionPayload;

    if (action.name === 'add_to_bundle') {
      addItem({
        system: payload.system || '',
        code: payload.code || '',
        display: payload.display || '',
      });
      return;
    }

    if (action.name === 'followup') {
      const followupType = payload.type;
      let query = '';

      if (followupType === 'meds_for_diagnosis') {
        const term = payload.display || payload.code;
        query = `medications to treat ${term}`;
      } else if (followupType === 'other_strengths') {
        const drug = payload.display || payload.query;
        query = `other dosages and forms of ${drug}`;
      } else if (followupType === 'diagnosis_for_drug') {
        const drug = payload.display || payload.query;
        query = `diagnosis codes for patients on ${drug}`;
      } else if (followupType === 'loinc_unit') {
        const test = payload.display || payload.query;
        query = `measurement unit for ${test}`;
      } else if (followupType === 'hcpcs_diagnosis') {
        query = `ICD-10 diagnosis codes related to ${payload.code}`;
      }

      if (query) {
        sendMessage({
          name: 'User',
          type: 'user_message',
          output: query,
        });
        return;
      }
    }

    console.log('Unhandled action:', action.name, action);
  };

  const payload = (action.payload || {}) as ActionPayload;
  const isInBundle =
    action.name === 'add_to_bundle' &&
    hasItem(payload.code || '', payload.system || '');

  return (
    <button
      onClick={handleClick}
      disabled={isInBundle}
      className={`px-3 py-1.5 text-sm rounded-lg transition-colors font-medium ${
        isInBundle
          ? 'bg-[var(--success-soft)] text-[var(--success)] cursor-default'
          : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-soft)] text-[var(--text-secondary)] hover:text-[var(--accent-primary)]'
      }`}
    >
      {isInBundle ? 'In Bundle' : action.label || action.name}
    </button>
  );
}
