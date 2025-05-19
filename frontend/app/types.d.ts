interface GoogleAccountsType {
  id: {
    initialize: (options: {
      client_id: string;
      callback: (response: { credential: string }) => void;
      auto_select?: boolean;
      cancel_on_tap_outside?: boolean;
    }) => void;
    renderButton: (
      element: HTMLElement,
      options: {
        type?: string;
        theme?: string;
        size?: string;
        text?: string;
        shape?: string;
        width?: number;
      }
    ) => void;
    prompt: () => void;
  };
}

interface Window {
  google?: {
    accounts: GoogleAccountsType;
  };
} 