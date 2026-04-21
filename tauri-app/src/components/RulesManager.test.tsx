import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RulesManager } from './RulesManager';

describe('RulesManager', () => {
  it('renders default rules when value is empty', () => {
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
      />
    );

    expect(screen.getByText('Remove filler words')).toBeInTheDocument();
    expect(screen.getByText('Remove repeated words')).toBeInTheDocument();
    expect(screen.getByText('Clean timestamps')).toBeInTheDocument();
    expect(screen.getByText('um|uh|ah|er|hmm')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Rule name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Regex pattern')).toBeInTheDocument();
    expect(screen.getByText('Add')).toBeInTheDocument();
  });

  it('parses legacy string format', async () => {
    const onChange = vi.fn();
    const legacyValue = '[^\\w\\s]+';

    render(
      <RulesManager
        value={legacyValue}
        onChange={onChange}
      />
    );

    await waitFor(() => {
      expect(onChange).toHaveBeenCalled();
    });

    const calls = onChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    const parsed = JSON.parse(lastCall);

    expect(parsed).toHaveLength(1);
    expect(parsed[0]).toMatchObject({
      id: 'legacy-regex',
      name: 'Legacy regex',
      pattern: legacyValue,
      enabled: true,
      is_builtin: false,
    });
  });

  it('parses JSON array format', () => {
    const onChange = vi.fn();
    const jsonValue = JSON.stringify([
      { id: 'custom-1', name: 'Custom Rule 1', pattern: 'test1', enabled: true, is_builtin: false },
      { id: 'custom-2', name: 'Custom Rule 2', pattern: 'test2', enabled: false, is_builtin: false },
    ]);

    render(
      <RulesManager
        value={jsonValue}
        onChange={onChange}
      />
    );

    expect(screen.getByText('Custom Rule 1')).toBeInTheDocument();
    expect(screen.getByText('Custom Rule 2')).toBeInTheDocument();
    expect(screen.getByText('test1')).toBeInTheDocument();
    expect(screen.getByText('test2')).toBeInTheDocument();
  });

  it('toggle rule calls onChange', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
      />
    );

    const switches = screen.getAllByRole('switch');
    await user.click(switches[0]);

    await waitFor(() => {
      expect(onChange).toHaveBeenCalled();
    });

    const calls = onChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    const parsed = JSON.parse(lastCall);

    const fillerWordsRule = parsed.find((r: any) => r.id === 'builtin-filler');
    expect(fillerWordsRule.enabled).toBe(false);
  });

  it('add new rule', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
      />
    );

    const ruleNameInput = screen.getByPlaceholderText('Rule name');
    const patternInput = screen.getByPlaceholderText('Regex pattern');
    const addButton = screen.getByText('Add');

    await user.type(ruleNameInput, 'Test Rule');
    await user.type(patternInput, '\\d+');
    await user.click(addButton);

    await waitFor(() => {
      expect(onChange).toHaveBeenCalled();
    });

    const calls = onChange.mock.calls;
    const lastCall = calls[calls.length - 1][0];
    const parsed = JSON.parse(lastCall);

    const newRule = parsed.find((r: any) => r.name === 'Test Rule');
    expect(newRule).toMatchObject({
      name: 'Test Rule',
      pattern: '\\d+',
      enabled: true,
      is_builtin: false,
    });
  });

  it('delete custom rule removes it from display', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const customRules = JSON.stringify([
      { id: 'custom-1', name: 'Custom Rule 1', pattern: 'test1', enabled: true, is_builtin: false },
      { id: 'custom-2', name: 'Custom Rule 2', pattern: 'test2', enabled: true, is_builtin: false },
    ]);

    render(
      <RulesManager
        value={customRules}
        onChange={onChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Custom Rule 1')).toBeInTheDocument();
      expect(screen.getByText('Custom Rule 2')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Delete');
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText('Custom Rule 1')).not.toBeInTheDocument();
    });

    expect(screen.getByText('Custom Rule 2')).toBeInTheDocument();
  });

  it('does not show delete button for builtin rules', () => {
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
      />
    );

    expect(screen.queryByText('Delete')).not.toBeInTheDocument();

    const fillerWordsRule = screen.getByText('Remove filler words').closest('div');
    const deleteButtons = fillerWordsRule?.querySelectorAll('button');
    expect(deleteButtons).toHaveLength(0);
  });

  it('disabled state hides add form', () => {
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
        disabled
      />
    );

    expect(screen.queryByPlaceholderText('Rule name')).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText('Regex pattern')).not.toBeInTheDocument();
    expect(screen.queryByText('Add')).not.toBeInTheDocument();
  });

  it('disabled state disables switches', () => {
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
        disabled
      />
    );

    const switches = screen.getAllByRole('switch');
    switches.forEach(switch_ => {
      expect(switch_).toBeDisabled();
    });
  });

  it('empty name/pattern prevents add', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
      />
    );

    const ruleNameInput = screen.getByPlaceholderText('Rule name');
    const patternInput = screen.getByPlaceholderText('Regex pattern');
    const addButton = screen.getByText('Add');

    await user.click(addButton);

    expect(onChange).not.toHaveBeenCalled();

    await user.type(ruleNameInput, 'Test Rule');
    await user.click(addButton);

    expect(onChange).not.toHaveBeenCalled();

    await user.type(patternInput, '\\d+');
    await user.click(addButton);

    expect(onChange).toHaveBeenCalled();
  });

  it('shows pattern in monospace font', () => {
    const onChange = vi.fn();
    render(
      <RulesManager
        value=""
        onChange={onChange}
      />
    );

    const patternElement = screen.getByText('um|uh|ah|er|hmm');
    expect(patternElement).toHaveClass('font-mono');
  });
});
