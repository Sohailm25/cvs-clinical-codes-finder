// ABOUTME: Application entry point with Chainlit and Recoil providers.
// ABOUTME: Wraps the app in necessary context providers for state management.

import React from 'react';
import ReactDOM from 'react-dom/client';
import { RecoilRoot } from 'recoil';
import { ChainlitContext } from '@chainlit/react-client';
import { apiClient } from './lib/chainlit';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChainlitContext.Provider value={apiClient}>
      <RecoilRoot>
        <App />
      </RecoilRoot>
    </ChainlitContext.Provider>
  </React.StrictMode>
);
