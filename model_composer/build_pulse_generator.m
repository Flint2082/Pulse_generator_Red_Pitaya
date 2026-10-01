function build_pulse_generator(n_pulses)
%BUILD_PULSE_GENERATOR Regenerate the out_1..out_3 pulse subsystems for N pulses per output.
%
%   build_pulse_generator(64)
%
%   Each output is a subsystem out_<k> with one input (counter) and one
%   output (pulse signal). Inside are n_pulses start/stop software registers
%   and the pulse logic. Only the inside of these subsystems is rebuilt;
%   nothing else in pulse_generator.slx is touched.
%
%   CASPER names registers after their path, so out_<k>/start_<p> appears in
%   the .fpg file as out_<k>_start_<p>, the same name the Python code uses.
%
%   The logic is: per pulse (counter >= start) AND (counter < stop), followed
%   by a two-level OR tree. Every block has latency 1, so the output lags the
%   counter by 4 clocks for any n_pulses and pulse timing does not shift when
%   n_pulses changes.
%
%   First run only: the old layout (pulse_logic_<k> referenced subsystems with
%   the registers at the top level) is replaced by the out_<k> subsystems,
%   keeping the counter input and output connections.
%
%   Run with the CASPER toolflow on the MATLAB path (after startsg). Save or
%   close the model first. Afterwards, compile the bitstream as usual; the
%   Python side reads the pulse count from the new .fpg file.

top = 'pulse_generator';
n_outputs = 3;

assert(n_pulses >= 2 && n_pulses == round(n_pulses), 'n_pulses must be an integer >= 2');

% Work in this folder so the model is found by name
prev_dir = cd(fileparts(mfilename('fullpath')));
restore_dir = onCleanup(@() cd(prev_dir));

if bdIsLoaded(top) && strcmp(get_param(top, 'Dirty'), 'on')
    error('%s has unsaved changes. Save or close it first.', top);
end
load_system(top);

for k = 1:n_outputs
    blk = sprintf('%s/out_%d', top, k);
    if getSimulinkBlockHandle(blk) == -1
        migrate_output(top, k);
    end
    build_output(blk, n_pulses);
end
save_system(top);

fprintf('Done: %d pulses per output, %d pulse registers in total.\n', n_pulses, 2*n_pulses*n_outputs);
end


function build_output(blk, n)
% Fill subsystem out_<k> with n pulses. Ports: in 1 = counter, out 1 = OR of all pulses.
clear_contents(blk);

% First OR level: groups of at least 8 pulses (at most ~sqrt(n) per group for large n),
% so the tree always has exactly two levels and a fixed latency.
n_groups = ceil(n / max(8, ceil(sqrt(n))));
group_edges = round(linspace(0, n, n_groups + 1));

for p = 0:n-1
    y = 80*p + 60;
    s = sprintf('start_%d', p);  e = sprintf('stop_%d', p);
    ge = sprintf('ge_%d', p);    lt = sprintf('lt_%d', p);  a = sprintf('and_%d', p);

    add_register(blk, s, [160 y-15    260 y+15]);
    add_register(blk, e, [160 y+25    260 y+55]);
    add_block('xbsIndex_r4/Relational', [blk '/' ge], 'mode', 'a>=b', 'latency', '1', ...
              'Position', [350 y-20 405 y+20]);
    add_block('xbsIndex_r4/Relational', [blk '/' lt], 'mode', 'a<b', 'latency', '1', ...
              'Position', [350 y+20 405 y+60]);
    add_block('xbsIndex_r4/Logical', [blk '/' a], 'logical_function', 'AND', 'inputs', '2', ...
              'latency', '1', 'Position', [480 y-5 535 y+45]);

    add_line(blk, 'counter/1', [ge '/1'], 'autorouting', 'smart');
    add_line(blk, [s '/1'],    [ge '/2'], 'autorouting', 'smart');
    add_line(blk, 'counter/1', [lt '/1'], 'autorouting', 'smart');
    add_line(blk, [e '/1'],    [lt '/2'], 'autorouting', 'smart');
    add_line(blk, [ge '/1'],   [a '/1'],  'autorouting', 'smart');
    add_line(blk, [lt '/1'],   [a '/2'],  'autorouting', 'smart');
end

for g = 1:n_groups
    members = group_edges(g) : group_edges(g+1) - 1;   % 0-based pulse indices
    or_g = sprintf('or_%d', g);
    add_block('xbsIndex_r4/Logical', [blk '/' or_g], 'logical_function', 'OR', ...
              'inputs', num2str(numel(members)), 'latency', '1', ...
              'Position', [640 80*members(1)+40 700 80*members(end)+110]);
    for i = 1:numel(members)
        add_line(blk, sprintf('and_%d/1', members(i)), sprintf('%s/%d', or_g, i), 'autorouting', 'smart');
    end
end

% Second OR level (a plain delay when there is only one group, to keep the latency the same)
y_mid = 40*n + 60;
if n_groups > 1
    add_block('xbsIndex_r4/Logical', [blk '/or_all'], 'logical_function', 'OR', ...
              'inputs', num2str(n_groups), 'latency', '1', 'Position', [800 y_mid-50 860 y_mid+50]);
else
    add_block('xbsIndex_r4/Delay', [blk '/or_all'], 'latency', '1', 'Position', [800 y_mid-20 860 y_mid+20]);
end
for g = 1:n_groups
    add_line(blk, sprintf('or_%d/1', g), sprintf('or_all/%d', g), 'autorouting', 'smart');
end

set_param([blk '/out'], 'Position', [950 y_mid-7 980 y_mid+7]);
add_line(blk, 'or_all/1', 'out/1', 'autorouting', 'smart');
end


function add_register(blk, name, pos)
% 32-bit From Processor software register with a Constant on its sim input.
reg = [blk '/' name];
add_block('xps_library/Memory/software_register', reg, ...
          'io_dir', 'From Processor', 'io_delay', '0', 'init_val', '0', ...
          'sample_period', '1', 'names', 'reg', 'bitwidths', '32', ...
          'bin_pts', '0', 'arith_types', '0', 'sim_port', 'on', 'show_format', 'on', ...
          'Position', pos);
add_block('built-in/Constant', [reg '_sim'], 'Value', '0', ...
          'Position', [pos(1)-80 pos(2) pos(1)-50 pos(4)]);
add_line(blk, [name '_sim/1'], [name '/1']);
end


function clear_contents(blk)
% Delete everything inside blk except the ports 'counter' and 'out' (created if missing),
% so the connections outside the subsystem stay intact.
lines = find_system(blk, 'SearchDepth', 1, 'FindAll', 'on', 'Type', 'line');
for h = lines'
    if ishandle(h), delete_line(h); end   % branches vanish together with their parent line
end
keep = {[blk '/counter'], [blk '/out']};
blocks = setdiff(find_system(blk, 'SearchDepth', 1, 'Type', 'block'), [{blk}, keep]);
cellfun(@delete_block, blocks);

if getSimulinkBlockHandle(keep{1}) == -1
    add_block('built-in/Inport', keep{1}, 'Port', '1', 'Position', [20 53 50 67]);
end
if getSimulinkBlockHandle(keep{2}) == -1
    add_block('built-in/Outport', keep{2}, 'Port', '1');
end
end


function migrate_output(top, k)
% One-time conversion of pulse_logic_<k> + top-level registers into subsystem out_<k>.
old = sprintf('%s/pulse_logic_%d', top, k);
if getSimulinkBlockHandle(old) == -1
    error('Neither %s/out_%d nor %s exists.', top, k, old);
end

% Remember what the counter input and the pulse output are connected to
pc = get_param(old, 'PortConnectivity');
src = get_param(pc(1).SrcBlock, 'PortHandles');
counter_src = src.Outport(pc(1).SrcPort + 1);
out_conn = pc(end);   % last entry = output port 1
out_dst = zeros(1, numel(out_conn.DstBlock));
for i = 1:numel(out_conn.DstBlock)
    dst = get_param(out_conn.DstBlock(i), 'PortHandles');
    out_dst(i) = dst.Inport(out_conn.DstPort(i) + 1);
end
pos = get_param(old, 'Position');

% Remove the top-level registers of this output and the Constants on their sim inputs
regs = find_system(top, 'SearchDepth', 1, 'RegExp', 'on', ...
                   'Name', sprintf('^out_%d_(start|stop)_\\d+$', k));
for i = 1:numel(regs)
    rc = get_param(regs{i}, 'PortConnectivity');
    sim_src = rc(1).SrcBlock;
    delete_block_and_lines(regs{i});
    if ~isempty(sim_src) && sim_src ~= -1 && strcmp(get_param(sim_src, 'BlockType'), 'Constant')
        delete_block_and_lines(sim_src);
    end
end
delete_block_and_lines(old);

% New plain subsystem in the same place, with only the counter input and pulse output
blk = sprintf('%s/out_%d', top, k);
add_block('built-in/Subsystem', blk, 'Position', [pos(1) pos(2) pos(3) pos(2)+50]);
clear_contents(blk);
ph = get_param(blk, 'PortHandles');
add_line(top, counter_src, ph.Inport(1), 'autorouting', 'smart');
for i = 1:numel(out_dst)
    add_line(top, ph.Outport(1), out_dst(i), 'autorouting', 'smart');
end
end


function delete_block_and_lines(blk)
lh = get_param(blk, 'LineHandles');
h = [lh.Inport, lh.Outport];
h = h(h ~= -1);
for i = 1:numel(h)
    if ishandle(h(i)), delete_line(h(i)); end
end
delete_block(blk);
end
