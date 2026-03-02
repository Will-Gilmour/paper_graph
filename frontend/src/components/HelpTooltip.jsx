/**
 * Help Tooltip Component
 * Shows helpful explanations for form fields
 */

import { useState } from 'react';
import './HelpTooltip.css';

export default function HelpTooltip({ text }) {
  const [show, setShow] = useState(false);

  return (
    <div className="help-tooltip">
      <span 
        className="help-icon"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      >
        ❓
      </span>
      {show && (
        <div className="help-bubble">
          {text}
        </div>
      )}
    </div>
  );
}

