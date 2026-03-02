import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PaperActions from '../PaperActions';

describe('PaperActions', () => {
  it('renders "Add to List" button when not in list', () => {
    const onToggle = vi.fn();
    render(<PaperActions doi="10.1234/test" isInList={false} onToggle={onToggle} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Add to List');
  });

  it('renders "Remove from List" button when in list', () => {
    const onToggle = vi.fn();
    render(<PaperActions doi="10.1234/test" isInList={true} onToggle={onToggle} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveTextContent('Remove from List');
  });

  it('calls onToggle with DOI when clicked', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<PaperActions doi="10.1234/test" isInList={false} onToggle={onToggle} />);
    
    const button = screen.getByRole('button');
    await user.click(button);
    
    expect(onToggle).toHaveBeenCalledWith('10.1234/test');
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('has correct background color for add state', () => {
    const onToggle = vi.fn();
    render(<PaperActions doi="10.1234/test" isInList={false} onToggle={onToggle} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveStyle({ background: '#228B22' }); // Green
  });

  it('has correct background color for remove state', () => {
    const onToggle = vi.fn();
    render(<PaperActions doi="10.1234/test" isInList={true} onToggle={onToggle} />);
    
    const button = screen.getByRole('button');
    expect(button).toHaveStyle({ background: '#dc3545' }); // Red
  });
});

