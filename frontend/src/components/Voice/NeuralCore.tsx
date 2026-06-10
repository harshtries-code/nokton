import React, { useEffect, useRef } from 'react';

type VoiceState = 'idle' | 'listening' | 'speaking' | 'thinking' | 'error';

interface NeuralCoreProps {
  state: VoiceState;
}

interface Particle {
  x: number; y: number; z: number;
  vx: number; vy: number; vz: number;
  size: number;
  baseAlpha: number;
  pulsePhase: number;
}

const STATE_CONFIG: Record<VoiceState, {
  primary: [number, number, number]; glow: string;
  speed: number; pulse: number; scatter: number;
  shake: number; breathe: number;
}> = {
  idle: {
    primary: [0, 212, 255], glow: 'rgba(0,212,255,0.04)',
    speed: 0.3, pulse: 0.5, scatter: 0, shake: 0, breathe: 0.02,
  },
  listening: {
    primary: [0, 240, 255], glow: 'rgba(0,240,255,0.08)',
    speed: 1.2, pulse: 2.5, scatter: 1.5, shake: 0, breathe: 0.05,
  },
  thinking: {
    primary: [139, 92, 246], glow: 'rgba(139,92,246,0.06)',
    speed: 0.8, pulse: 1.0, scatter: 0.3, shake: 0, breathe: 0.015,
  },
  speaking: {
    primary: [168, 85, 247], glow: 'rgba(168,85,247,0.06)',
    speed: 1.0, pulse: 3.0, scatter: 0.8, shake: 0, breathe: 0.04,
  },
  error: {
    primary: [239, 68, 68], glow: 'rgba(239,68,68,0.05)',
    speed: 0.15, pulse: 0.3, scatter: 0, shake: 4, breathe: 0.01,
  },
};

export function NeuralCore({ state }: NeuralCoreProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<VoiceState>(state);
  const mouseRef = useRef<{ x: number; y: number }>({ x: -999, y: -999 });

  useEffect(() => { stateRef.current = state; }, [state]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const dpr = window.devicePixelRatio || 1;
    let cw = canvas.offsetWidth;
    let ch = canvas.offsetHeight;
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    ctx.scale(dpr, dpr);

    const onResize = () => {
      cw = canvas.offsetWidth;
      ch = canvas.offsetHeight;
      canvas.width = cw * dpr;
      canvas.height = ch * dpr;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
    };
    window.addEventListener('resize', onResize);

    const onMouse = (e: MouseEvent) => {
      const r = canvas.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    canvas.addEventListener('mousemove', onMouse);
    canvas.addEventListener('mouseleave', () => {
      mouseRef.current = { x: -999, y: -999 };
    });

    // Create free-floating particles spread across the viewport
    const particles: Particle[] = [];
    const count = 80;
    for (let i = 0; i < count; i++) {
      const spread = 200;
      particles.push({
        x: (Math.random() - 0.5) * spread * 2,
        y: (Math.random() - 0.5) * spread * 2,
        z: (Math.random() - 0.5) * spread,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        vz: (Math.random() - 0.5) * 0.15,
        size: 1.0 + Math.random() * 2.5,
        baseAlpha: 0.2 + Math.random() * 0.6,
        pulsePhase: Math.random() * Math.PI * 2,
      });
    }

    let t = 0;

    const render = () => {
      ctx.clearRect(0, 0, cw, ch);
      t += 0.02;
      const cx = cw / 2;
      const cy = ch / 2;
      const st = stateRef.current;
      const cfg = STATE_CONFIG[st];
      const [cr, cg, cb] = cfg.primary;

      const shakeX = cfg.shake ? (Math.random() - 0.5) * cfg.shake : 0;
      const shakeY = cfg.shake ? (Math.random() - 0.5) * cfg.shake : 0;

      // Subtle background atmosphere
      const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, cw * 0.5);
      bgGrad.addColorStop(0, cfg.glow);
      bgGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, cw, ch);

      // Update & draw particles
      const fov = 400;
      const centerDist = 200;

      // Sort by Z for depth ordering
      particles.sort((a, b) => b.z - a.z);

      for (const p of particles) {
        // Movement — drift freely, react to state
        p.x += p.vx * cfg.speed;
        p.y += p.vy * cfg.speed;
        p.z += p.vz * cfg.speed;

        // Scatter effect for listening/speaking
        if (cfg.scatter > 0) {
          p.vx += (Math.random() - 0.5) * cfg.scatter * 0.02;
          p.vy += (Math.random() - 0.5) * cfg.scatter * 0.02;
          p.vz += (Math.random() - 0.5) * cfg.scatter * 0.01;
        }

        // Gentle gravity toward center (keeps particles from flying away)
        const dx = -p.x;
        const dy = -p.y;
        const dz = -p.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist > 30) {
          const gravity = 0.0003 * Math.min(dist, 300);
          p.vx += (dx / dist) * gravity;
          p.vy += (dy / dist) * gravity;
          p.vz += (dz / dist) * gravity;
        }

        // Damping
        p.vx *= 0.998;
        p.vy *= 0.998;
        p.vz *= 0.998;

        // Speed limit
        const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy + p.vz * p.vz);
        if (speed > 2) {
          const s = 2 / speed;
          p.vx *= s; p.vy *= s; p.vz *= s;
        }

        // Wrap-around boundary (soft)
        const bound = 300;
        if (Math.abs(p.x) > bound) p.vx -= Math.sign(p.x) * 0.1;
        if (Math.abs(p.y) > bound) p.vy -= Math.sign(p.y) * 0.1;
        if (Math.abs(p.z) > bound / 2) p.vz -= Math.sign(p.z) * 0.05;

        // Project to 2D
        const perspective = fov / (fov + p.z + centerDist);
        const sx = cx + p.x * perspective + shakeX;
        const sy = cy + p.y * perspective + shakeY;
        const projSize = p.size * perspective;

        // Mouse repulsion
        const mdx = mouseRef.current.x - sx;
        const mdy = mouseRef.current.y - sy;
        const md = Math.sqrt(mdx * mdx + mdy * mdy);
        let drawX = sx;
        let drawY = sy;
        if (md < 120 && md > 0) {
          const force = (120 - md) / 120;
          // Push away from mouse
          drawX -= (mdx / md) * force * 30;
          drawY -= (mdy / md) * force * 30;
          // Also affect velocity
          p.vx -= (mdx / md) * force * 0.3;
          p.vy -= (mdy / md) * force * 0.3;
        }

        // Pulsing alpha
        const pulseAlpha = Math.sin(t * cfg.pulse + p.pulsePhase) * 0.3 + 0.7;
        const depthAlpha = Math.max(0.1, (centerDist - p.z) / (centerDist * 2));
        const alpha = p.baseAlpha * pulseAlpha * depthAlpha;

        // Draw particle with glow
        ctx.beginPath();
        ctx.arc(drawX, drawY, projSize, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${alpha})`;
        ctx.shadowBlur = st !== 'idle' ? projSize * 6 : projSize * 3;
        ctx.shadowColor = `rgba(${cr},${cg},${cb},${alpha * 0.6})`;
        ctx.fill();
      }

      ctx.shadowBlur = 0;

      // Subtle center breathing glow
      const breathSize = 40 + Math.sin(t * 0.5) * 10 * cfg.breathe * 50;
      const coreGrad = ctx.createRadialGradient(cx + shakeX, cy + shakeY, 0, cx + shakeX, cy + shakeY, breathSize);
      coreGrad.addColorStop(0, `rgba(${cr},${cg},${cb},0.06)`);
      coreGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx + shakeX, cy + shakeY, breathSize, 0, Math.PI * 2);
      ctx.fill();

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', onResize);
      canvas.removeEventListener('mousemove', onMouse);
    };
  }, []);

  return (
    <div style={styles.container}>
      <canvas ref={canvasRef} style={styles.canvas} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    overflow: 'hidden',
  },
  canvas: {
    width: '100%',
    height: '100%',
    display: 'block',
  },
};
