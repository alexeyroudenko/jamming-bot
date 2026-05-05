import { useEffect, useState, useRef, useCallback } from 'react';
import io from 'socket.io-client';
import { Url } from '../../constants';
import { normalizeStep } from './normalizeStep';

const MAX_STEPS = 2000;

export function useStepsDataset() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [steps, setSteps] = useState([]);
  const [source, setSource] = useState('api/steps');

  const mergeStep = useCallback((msg) => {
    setSteps((prev) => {
      const norm = normalizeStep(msg, (prev[prev.length - 1]?._n || 0) + 1);
      const idx = prev.findIndex((r) => r._n === norm._n);
      let next;
      if (idx >= 0) {
        next = [...prev];
        next[idx] = { ...next[idx], ...norm };
      } else {
        next = [...prev, norm];
        if (next.length > MAX_STEPS) next = next.slice(-MAX_STEPS);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setNotice(null);
      try {
        const res = await fetch(`${Url}/api/steps/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const arr = Array.isArray(data) ? data : (data && data.data) || [];
        const mapped = arr.map((row, i) => normalizeStep(row, i + 1));
        if (!cancelled) {
          setSteps(mapped);
          setSource('api/steps');
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message || String(e));
          setSteps([]);
          setNotice(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const socket = io(Url, { transports: ['websocket', 'polling'] });
    socket.on('connect', () => socket.emit('consumer'));
    socket.on('step', (msg) => mergeStep(msg));
    return () => {
      socket.disconnect();
    };
  }, [mergeStep]);

  return { loading, error, source, notice, steps };
}
