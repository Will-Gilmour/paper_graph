import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import usePapersOfInterest from '../usePapersOfInterest';

describe('usePapersOfInterest', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes with empty collection', () => {
    const { result } = renderHook(() => usePapersOfInterest());
    
    expect(result.current.count).toBe(0);
    expect(result.current.papersOfInterest.size).toBe(0);
  });

  it('adds papers to collection', () => {
    const { result } = renderHook(() => usePapersOfInterest());
    
    act(() => {
      result.current.addPaper('10.1234/test');
    });
    
    expect(result.current.count).toBe(1);
    expect(result.current.hasPaper('10.1234/test')).toBe(true);
  });

  it('removes papers from collection', () => {
    const { result } = renderHook(() => usePapersOfInterest());
    
    act(() => {
      result.current.addPaper('10.1234/test');
      result.current.removePaper('10.1234/test');
    });
    
    expect(result.current.count).toBe(0);
    expect(result.current.hasPaper('10.1234/test')).toBe(false);
  });

  it('toggles papers in collection', () => {
    const { result } = renderHook(() => usePapersOfInterest());
    
    act(() => {
      result.current.togglePaper('10.1234/test');
    });
    expect(result.current.hasPaper('10.1234/test')).toBe(true);
    
    act(() => {
      result.current.togglePaper('10.1234/test');
    });
    expect(result.current.hasPaper('10.1234/test')).toBe(false);
  });

  it('clears all papers', () => {
    const { result } = renderHook(() => usePapersOfInterest());
    
    act(() => {
      result.current.addPaper('10.1234/test1');
      result.current.addPaper('10.1234/test2');
      result.current.clearAll();
    });
    
    expect(result.current.count).toBe(0);
  });

  it('persists to localStorage', () => {
    const { result } = renderHook(() => usePapersOfInterest());
    
    act(() => {
      result.current.addPaper('10.1234/test');
    });
    
    // Check localStorage
    const stored = JSON.parse(localStorage.getItem('litsearch_papers_of_interest'));
    expect(stored).toContain('10.1234/test');
  });

  it('loads from localStorage on init', () => {
    // Pre-populate localStorage
    localStorage.setItem('litsearch_papers_of_interest', JSON.stringify(['10.1234/existing']));
    
    const { result } = renderHook(() => usePapersOfInterest());
    
    expect(result.current.count).toBe(1);
    expect(result.current.hasPaper('10.1234/existing')).toBe(true);
  });
});

