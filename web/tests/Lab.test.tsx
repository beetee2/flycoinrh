import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Lab } from '../src/Lab';
import { MOTORS, parseLabResult, parseLabStatus, preset } from '../src/lab-contracts';
import type { LabResult } from '../src/lab-contracts';

// Synthetic response and mocked HTTP only. These tests do not establish real-model behavior.
const status = { state:'ready',message:'Local model available',attempted_calls:0,call_cap:256,seeds:[17,29,43],calls_per_comparison:9 };
function fixture(a = preset('Vertical stripes'), b = preset('Horizontal stripes')): LabResult {
  const rates = Object.fromEntries(MOTORS.map((m,i) => [m,i+0.125])) as LabResult['samples'][number]['motor_rates_hz'];
  const populations = { neuron_indices:[0],body_ids:[100],pixel_indices:[0],sampled_pixels_u8:[0],drive_hz:[50],coverage_counts:Array.from({length:256},(_,i) => i === 0 ? 1 : 0),missing_coordinates:0 };
  const retina = { populations:{L1:populations,L2:populations},union_coverage_counts:Array.from({length:256},(_,i) => i === 0 ? 2 : 0),sampled_pixel_count:1,discarded_pixel_indices:Array.from({length:255},(_,i) => i+1) };
  return {
    schema_version:'flytrap-lab-result-1', result_id:'a'.repeat(32),created_at:'2026-09-11T12:00:00Z',cached:false,fixture:false,
    request:{schema_version:'flytrap-lab-request-1',a,b},seeds:[17,29,43],
    samples:[17,29,43].flatMap(seed => (['A','A_repeat','B'] as const).map(side => ({side,seed,motor_rates_hz:{...rates},statistics:{sampled_neurons:2,spike_count:4,firing:2,spikes_per_sec:200,mean_mv:-55.5,visual:1,motor:1},neural_ms:20}))),
    retina:{A:retina,B:retina},comparison:{same_image:JSON.stringify(a)===JSON.stringify(b),equal_brightness:a.reduce((s,v)=>s+v,0)===b.reduce((s,v)=>s+v,0),mean_brightness_u8:{A:a.reduce((s,v)=>s+v,0)/256,B:b.reduce((s,v)=>s+v,0)/256},same_seed_repeatable:true,motor_rates_hz:Object.fromEntries(MOTORS.map(m=>[m,{a_mean:rates[m],b_mean:rates[m],a_sd:0,b_sd:0,delta_mean:0,delta_sd:0,paired_deltas:[0,0,0]}])) as LabResult['comparison']['motor_rates_hz']},identities:{model:{test_only:'SYNTHETIC UI FIXTURE'},graph_manifest_sha256:'0'.repeat(64),source_head:'0'.repeat(40),source_sha256:{'fixture':'0'.repeat(64)},source_tree_sha256:'0'.repeat(64),runtime:{fixture:true},input_sha256:{A:'0'.repeat(64),B:'0'.repeat(64)},encoding:'synthetic UI fixture',comparison:'synthetic UI fixture',statistics:'synthetic UI fixture',limitations:'No real-model evidence'},attempted_calls:9,
  };
}
function mock(result: unknown = fixture()) {
  const fetcher = vi.fn().mockResolvedValueOnce({ok:true,json:async()=>status}).mockResolvedValue({ok:true,json:async()=>result});
  vi.stubGlobal('fetch',fetcher);return fetcher;
}
async function ready() { expect(await screen.findByText(/Ready · Local model available/)).toBeInTheDocument(); }

describe('P00 UI contracts (synthetic data; no real model)', () => {
  it('presets remain bounded and stripes have equal brightness', () => {
    for(const name of ['Black','White','Vertical stripes','Horizontal stripes','Checkerboard']) {
      const p = preset(name);expect(p).toHaveLength(256);expect(p.every(v=>Number.isInteger(v)&&v>=0&&v<=255)).toBe(true);
    }
    expect(preset('Vertical stripes')).not.toEqual(preset('Horizontal stripes'));
    expect(preset('Vertical stripes').reduce((a,b)=>a+b,0)).toEqual(preset('Horizontal stripes').reduce((a,b)=>a+b,0));
  });
  it('round-trips result JSON and rejects malformed payloads', () => {
    const f=fixture(); expect(parseLabResult(JSON.parse(JSON.stringify(f)))).toEqual(f);
    expect(()=>parseLabResult({...f,request:{...f.request,a:[1]}})).toThrow('Invalid result schema');
    expect(()=>parseLabResult({...f,samples:f.samples.slice(1)})).toThrow();
    expect(()=>parseLabResult({...f,seeds:[17,17,17]})).toThrow();
    expect(()=>parseLabResult({...f,samples:Array(9).fill(f.samples[0])})).toThrow();
    const misaligned=structuredClone(f);misaligned.retina.A.populations.L1.drive_hz=[];expect(()=>parseLabResult(misaligned)).toThrow();
    expect(()=>parseLabResult({...f,unexpected:true})).toThrow();
    expect(()=>parseLabResult({...f,identities:{}})).toThrow();
    expect(()=>parseLabResult({...f,attempted_calls:257})).toThrow();
    expect(()=>parseLabStatus({...status,seeds:[1,2,3]})).toThrow();
  });
  it('renders bounded editors and submits exactly edited pixels only on Run', async () => {
    const fetcher=mock();render(<Lab/>);await ready();
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(screen.getAllByRole('button',{name:/pixel row/})).toHaveLength(512);
    fireEvent.change(screen.getByRole('slider',{name:'Brush intensity for A'}),{target:{value:'73'}});
    const pixel=screen.getByRole('button',{name:'A pixel row 1 column 1: 0'});pixel.focus();await userEvent.keyboard('{Enter}');
    expect(screen.getByRole('button',{name:'A pixel row 1 column 1: 73'})).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Preset for B'}),'Black');
    const a=preset('Vertical stripes');a[0]=73;
    fetcher.mockResolvedValue({ok:true,json:async()=>fixture(a,preset('Black'))});
    await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    await screen.findByRole('region',{name:'Comparison result'});
    const body=JSON.parse(fetcher.mock.calls[1][1].body);expect(body).toEqual({schema_version:'flytrap-lab-request-1',a,b:preset('Black')});
    expect(screen.getByTestId('submitted-A').textContent?.trim().split(/\s+/).map(Number)).toEqual(a);
    expect(screen.getByRole('img',{name:'Exact submitted pattern A'})).toBeInTheDocument();
  });
  it('paints across pointer-captured touch cells without changing the other input', async () => {
    mock();render(<Lab/>);await ready();
    const grid=screen.getByRole('group',{name:'Pattern A pixels'});
    const first=screen.getByRole('button',{name:'A pixel row 1 column 1: 0'});
    const third=screen.getByRole('button',{name:'A pixel row 1 column 3: 0'});
    // jsdom has no layout hit-testing; emulate the captured touch's actual hit cell.
    const original=document.elementFromPoint;
    document.elementFromPoint=vi.fn().mockReturnValue(third);
    vi.stubGlobal('PointerEvent',MouseEvent);
    fireEvent.pointerDown(first,{button:0,buttons:1,pointerType:'touch'});
    fireEvent.pointerMove(grid,{buttons:1,clientX:20,clientY:20,pointerType:'touch'});
    fireEvent.pointerUp(grid,{button:0,buttons:0,pointerType:'touch'});
    expect(screen.getByRole('button',{name:'A pixel row 1 column 1: 255'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'A pixel row 1 column 3: 255'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'B pixel row 1 column 3: 0'})).toBeInTheDocument();
    document.elementFromPoint=original;
  });
  it('displays honest drive labels, discarded information, raw rates and different-seed variation', async () => {
    mock();render(<Lab/>);await ready();await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    await screen.findByRole('region',{name:'Comparison result'});
    expect(screen.getByText(/input drive is not neuron firing/)).toBeInTheDocument();
    expect(screen.getAllByText(/255 pixels discarded/)).toHaveLength(2);
    expect(screen.getByText(/Same-seed A repeatability: PASS/)).toBeInTheDocument();
    expect(screen.getByText(/Different-seed variation is reported separately/)).toBeInTheDocument();
    expect(screen.getByText(/Matching motor rates do not establish identical whole-brain activity/)).toBeInTheDocument();
    expect(screen.getByTestId('rate-A-17-steer_L')).toHaveTextContent('0.1250');
    expect(screen.getByTestId('mean-A-steer_L')).toHaveTextContent('0.1250 ± 0');
    expect(screen.getByText(/Equal mean brightness/)).toBeInTheDocument();
    expect(screen.getByText(/distinct neurons firing at least once during the 20 ms window/)).toBeInTheDocument();
  });
  it('copies A into B for a same-image control and marks edited results as stale', async () => {
    const a=preset('Vertical stripes');mock(fixture(a,a));render(<Lab/>);await ready();
    await userEvent.click(screen.getByRole('button',{name:/Copy A to B/}));
    await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    expect(await screen.findByText('Same-image control')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Preset for A'}),'Black');
    expect(screen.getByText(/Editors changed after this run/)).toBeInTheDocument();
    expect(screen.getByTestId('submitted-A').textContent?.trim().split(/\s+/).map(Number)).toEqual(a);
  });
  it('keeps one explicit request active and locks input while running', async () => {
    const fetcher=mock();fetcher.mockImplementation(()=>new Promise(()=>{}));
    render(<Lab/>);await ready();await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    expect(screen.getByRole('button',{name:/Running comparison/})).toBeDisabled();
    expect(screen.getByRole('combobox',{name:'Preset for A'})).toBeDisabled();
    expect(screen.getByText(/one isolated model job is running/)).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it.each([409,503])('shows HTTP %s failures and allows explicit retry', async code => {
    const fetcher=mock();fetcher.mockResolvedValue({ok:false,status:code,json:async()=>({detail:code===409?'Another model job is active.':'Real model unavailable.'})});
    render(<Lab/>);await ready();await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    expect(await screen.findByRole('alert')).toHaveTextContent(code===409?'Another model job is active.':'Real model unavailable.');
    expect(screen.queryByRole('region',{name:'Comparison result'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Run comparison/})).toBeEnabled();
  });
  it.each([{...status,state:'unavailable'},{...status,state:'busy'},{...status,attempted_calls:252}])('disables Run when unavailable, externally busy, or capped: %o', async s => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>s}));render(<Lab/>);
    await waitFor(()=>expect(screen.getByRole('status',{name:'Local model status'})).toHaveTextContent(s.message));
    expect(screen.getByRole('button',{name:/Run comparison/})).toBeDisabled();
  });
  it('rejects malformed results without displaying invented output', async () => {
    mock({...fixture(),samples:[]});render(<Lab/>);await ready();await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid result schema');
    expect(screen.queryByRole('region',{name:'Comparison result'})).not.toBeInTheDocument();
  });
  it('rejects output from different input pixels', async () => {
    mock(fixture(preset('Black')));render(<Lab/>);await ready();await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    expect(await screen.findByRole('alert')).toHaveTextContent('result pixels do not match');
  });
  it('downloads the exact displayed result JSON', async () => {
    const f=fixture();mock(f);const create=vi.fn().mockReturnValue('blob:fixture');const revoke=vi.fn();
    vi.stubGlobal('URL',{createObjectURL:create,revokeObjectURL:revoke});
    const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
    render(<Lab/>);await ready();await userEvent.click(screen.getByRole('button',{name:/Run comparison/}));
    await userEvent.click(await screen.findByRole('button',{name:'Download result JSON'}));
    const blob=create.mock.calls[0][0] as Blob;
    const text=await new Promise<string>(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result as string);reader.readAsText(blob);});
    expect(parseLabResult(JSON.parse(text))).toEqual(f);expect(click).toHaveBeenCalledTimes(1);click.mockRestore();
    expect(within(screen.getByRole('table',{name:'Raw motor rates'})).getAllByRole('row')).toHaveLength(10);
  });
});
