function build_pulse_generator(n_pulses)
%BUILD_PULSE_GENERATOR Regenerate the pulse registers and pulse logic for N pulses per output.
%
%   build_pulse_generator(64)
%
%   Rebuilds pulse_logic.slx (the referenced subsystem used by pulse_logic_1..3)
%   and the out_<k>_start_<p> / out_<k>_stop_<p> software registers in
%   pulse_generator.slx, then saves both models. Everything else in the
%   top-level model (counter, From blocks, outputs, control registers) is left
%   untouched.
%
%   The generated logic is the same as the hand-built version: per pulse
%   (counter >= start) AND (counter < stop), followed by a two-level OR tree.
%   Every block has latency 1, so the total latency is 4 clocks for any
%   n_pulses and pulse timing does not shift when n_pulses changes.
%
%   Run with the CASPER toolflow on the MATLAB path (after startsg). Save or
%   close both models first. Afterwards, compile the bitstream as usual; the
%   Python side reads the pulse count from the new .fpg file.

top = 'pulse_generator';
sub = 'pulse_logic';
n_outputs = 3;

assert(n_pulses >= 2 && n_pulses == round(n_pulses), 'n_pulses must be an integer >= 2');

% Work in this folder so both models are found by name
prev_dir = cd(fileparts(mfilename('fullpath')));
restore_dir = onCleanup(@() cd(prev_dir));

for m = {top, sub}
    if bdIsLoaded(m{1}) && strcmp(get_param(m{1}, 'Dirty'), 'on')
        error('%s has unsaved changes. Save or close it first.', m{1});
    end
end
% Close the top model so the pulse_logic_<k> instances pick up the new port count on reload
if bdIsLoaded(top), close_system(top, 0); end

build_pulse_logic(sub, n_pulses);

load_system(top);
for k = 1:n_outputs
    rebuild_registers(top, k, n_pulses);
end
save_system(top);

fprintf('Done: %d pulses per output, %d pulse registers in total.\n', n_pulses, 2*n_pulses*n_outputs);
end


function build_pulse_logic(sub, n)
% Fill the pulse_logic subsystem with n start/stop comparator pairs.
% Ports: 1 = counter, 2p = start_p, 2p+1 = stop_p (p = 1..n), out = OR of all pulses.
load_system(sub);
clear_diagram(sub);

add_block('built-in/Inport', [sub '/counter'], 'Port', '1', 'Position', [20 13 50 27]);

% First OR level: groups of at least 8 pulses (at most ~sqrt(n) per group for large n),
% so the tree always has exactly two levels and a fixed latency.
n_groups = ceil(n / max(8, ceil(sqrt(n))));
group_edges = round(linspace(0, n, n_groups + 1));

for p = 1:n
    y = 80*p;
    s = sprintf('start_%d', p);  e = sprintf('stop_%d', p);
    ge = sprintf('ge_%d', p);    lt = sprintf('lt_%d', p);  a = sprintf('and_%d', p);

    add_block('built-in/Inport', [sub '/' s], 'Port', num2str(2*p),   'Position', [100 y    130 y+14]);
    add_block('built-in/Inport', [sub '/' e], 'Port', num2str(2*p+1), 'Position', [100 y+40 130 y+54]);
    add_block('xbsIndex_r4/Relational', [sub '/' ge], 'mode', 'a>=b', 'latency', '1', ...
              'Position', [250 y-15 305 y+25]);
    add_block('xbsIndex_r4/Relational', [sub '/' lt], 'mode', 'a<b', 'latency', '1', ...
              'Position', [250 y+25 305 y+65]);
    add_block('xbsIndex_r4/Logical', [sub '/' a], 'logical_function', 'AND', 'inputs', '2', ...
              'latency', '1', 'Position', [400 y 455 y+50]);

    add_line(sub, 'counter/1', [ge '/1'], 'autorouting', 'smart');
    add_line(sub, [s '/1'],    [ge '/2'], 'autorouting', 'smart');
    add_line(sub, 'counter/1', [lt '/1'], 'autorouting', 'smart');
    add_line(sub, [e '/1'],    [lt '/2'], 'autorouting', 'smart');
    add_line(sub, [ge '/1'],   [a '/1'],  'autorouting', 'smart');
    add_line(sub, [lt '/1'],   [a '/2'],  'autorouting', 'smart');
end

for g = 1:n_groups
    members = group_edges(g)+1 : group_edges(g+1);
    or_g = sprintf('or_%d', g);
    add_block('xbsIndex_r4/Logical', [sub '/' or_g], 'logical_function', 'OR', ...
              'inputs', num2str(numel(members)), 'latency', '1', ...
              'Position', [600 80*members(1) 660 80*members(end)+50]);
    for i = 1:numel(members)
        add_line(sub, sprintf('and_%d/1', members(i)), sprintf('%s/%d', or_g, i), 'autorouting', 'smart');
    end
end

% Second OR level (a plain delay when there is only one group, to keep the latency the same)
y_mid = 40*n;
if n_groups > 1
    add_block('xbsIndex_r4/Logical', [sub '/or_all'], 'logical_function', 'OR', ...
              'inputs', num2str(n_groups), 'latency', '1', 'Position', [800 y_mid-50 860 y_mid+50]);
else
    add_block('xbsIndex_r4/Delay', [sub '/or_all'], 'latency', '1', 'Position', [800 y_mid-20 860 y_mid+20]);
end
for g = 1:n_groups
    add_line(sub, sprintf('or_%d/1', g), sprintf('or_all/%d', g), 'autorouting', 'smart');
end

add_block('built-in/Outport', [sub '/out'], 'Port', '1', 'Position', [950 y_mid-7 980 y_mid+7]);
add_line(sub, 'or_all/1', 'out/1', 'autorouting', 'smart');

save_system(sub);
close_system(sub);
end


function rebuild_registers(top, k, n)
% Replace the out_<k>_start_<p> / out_<k>_stop_<p> registers (p = 0..n-1) and the
% Constant blocks driving their sim inputs, and wire them to pulse_logic_<k>.
pl = sprintf('%s/pulse_logic_%d', top, k);

old = find_system(top, 'SearchDepth', 1, 'RegExp', 'on', ...
                  'Name', sprintf('^out_%d_(start|stop)_\\d+$', k));
for i = 1:numel(old)
    pc = get_param(old{i}, 'PortConnectivity');
    sim_src = pc(1).SrcBlock;   % block driving the sim input
    delete_block_and_lines(old{i});
    if ~isempty(sim_src) && sim_src ~= -1 && strcmp(get_param(sim_src, 'BlockType'), 'Constant')
        delete_block_and_lines(sim_src);
    end
end

ports = get_param(pl, 'Ports');
if ports(1) ~= 2*n + 1
    error('%s has %d inputs, expected %d. Is pulse_logic.slx up to date?', pl, ports(1), 2*n + 1);
end

% Resize pulse_logic_<k> so each port lines up with a 40 px row
pitch = 40;
pos = get_param(pl, 'Position');
set_param(pl, 'Position', [pos(1) pos(2) pos(3) pos(2) + pitch*(2*n + 1)]);

kinds = {'start', 'stop'};
for p = 0:n-1
    for j = 1:2
        port = 2 + 2*p + (j - 1);
        yc = pos(2) + pitch*(port - 0.5);
        reg = sprintf('out_%d_%s_%d', k, kinds{j}, p);
        sim = [reg '_sim'];

        add_block('xps_library/Memory/software_register', [top '/' reg], ...
                  'io_dir', 'From Processor', 'io_delay', '0', 'init_val', '0', ...
                  'sample_period', '1', 'names', 'reg', 'bitwidths', '32', ...
                  'bin_pts', '0', 'arith_types', '0', 'sim_port', 'on', 'show_format', 'on', ...
                  'Position', [pos(1)-165 yc-15 pos(1)-65 yc+15]);
        add_block('built-in/Constant', [top '/' sim], 'Value', '0', ...
                  'Position', [pos(1)-275 yc-15 pos(1)-245 yc+15]);

        add_line(top, [sim '/1'], [reg '/1']);
        add_line(top, [reg '/1'], sprintf('pulse_logic_%d/%d', k, port));
    end
end
end


function clear_diagram(sys)
% Delete all lines and blocks at the top level of sys.
lines = find_system(sys, 'SearchDepth', 1, 'FindAll', 'on', 'Type', 'line');
for h = lines'
    if ishandle(h), delete_line(h); end   % branches vanish together with their parent line
end
blocks = find_system(sys, 'SearchDepth', 1, 'Type', 'block');
cellfun(@delete_block, blocks);
end


function delete_block_and_lines(blk)
lh = get_param(blk, 'LineHandles');
h = [lh.Inport, lh.Outport];
h = h(h ~= -1);
if ~isempty(h), delete_line(h); end
delete_block(blk);
end
