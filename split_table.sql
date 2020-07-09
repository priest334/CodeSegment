create table pb (
	pf numeric(16,0),
	df text
);

CREATE OR REPLACE FUNCTION _default_init_script(tbl text)
RETURNS boolean AS $$
BEGIN
	raise notice 'init partitioned table here';
	return true;
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION create_child_table(
    parent text,
    child text,
    field text,
	minval numeric,
	maxval numeric,
    init_script text)
RETURNS text AS $$
DECLARE
	sql text := '';
	trname text := '';
	cond text := '';
	trcond text := '';
BEGIN
	trname := '_deftr_insert_into_'||child;
	if (minval is null) then
		cond := field||'<'||maxval;
		trcond := 'New.'||field||'<'||maxval;
	else
		cond := field||'>='||minval||' and '||field||'<'||maxval;
		trcond := 'New.'||field||'>='||minval||' and New.'||field||'<'||maxval;
	end if;
	sql := 'create table '||child||'(check('||cond||')) inherits ('||parent||')';
	raise notice 'sql: %', sql;
	execute sql;
	sql := 'select '||init_script||'('''||child||''')';
	raise notice 'sql: %', sql;
	execute sql;
	sql := 'CREATE OR REPLACE FUNCTION '||trname||'()
			RETURNS TRIGGER AS $inner$ BEGIN
				insert into '||child||' values (New.*);
				RETURN NULL;
			END;
			$inner$
			language plpgsql';
	raise notice 'sql: %', sql;
	execute sql;
	sql := 'create trigger '||child||'_tr before insert on '||parent||'
			for each row when('||trcond||') 
			execute procedure '||trname||'()';
	raise notice 'sql: %', sql;	
	execute sql;
	return '';
END;
$$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION new_child_table(
	parent text,
	field text,
	intvl text,
	stime timestamp
)
RETURNS text AS $$
DECLARE
	minval numeric := 0;
	maxval numeric := 0;
	curmax timestamp := null;
	arr text[];
	sql text := '';
	tmp text := '';
	fmt text := '';
	name text := '';
BEGIN
	select regexp_matches(''||intvl||'', '^(\d+)([d|m|y])$') into arr;
	if (arr is null) then
		return 'invalid parameter: '||intvl;
	end if;
	sql := 'select to_number(substr(table_name, length('''||parent||''')+2),''9999999999'') 
		from information_schema.tables where table_name like '''||parent||'_%''  order by table_name desc limit 1';
	raise notice 'sql: %', sql;
	execute sql into tmp;
	case arr[2]
		when 'd' then
			fmt = 'YYYYMMDD';
			if (tmp is not null) then
				sql := 'select regexp_replace('''||tmp||''', ''(\d{4})(\d{2})(\d{2})'', ''\1-\2-\3 00:00:00'')';
				raise notice 'sql: %', sql;
				execute sql into tmp;
				if (tmp is not null) then
					sql := 'select timestamptz '''||tmp||'''';
					execute sql into curmax;
					stime = curmax;
				end if;
			end if;
			sql := 'select to_char(date_trunc(''day'', timestamptz '''||stime||'''), ''YYYY-MM-DD HH24:MI:SS'')';
			raise notice 'sql: %', sql;
			execute sql into tmp;
			sql := 'select extract(epoch from timestamptz '''||tmp||''')';
			execute sql into minval;
			sql := 'select to_char(date_trunc(''day'', timestamptz '''||stime||''') + '''||arr[1]||' days'', ''YYYY-MM-DD HH24:MI:SS'')';
			execute sql into tmp;	
			sql := 'select extract(epoch from timestamptz '''||tmp||''')';
			execute sql into maxval;
		when 'm' then
			fmt = 'YYYYMM';
			if (tmp is not null) then
				sql := 'select regexp_replace('''||tmp||''', ''(\d{4})(\d{2})'', ''\1-\2-01 00:00:00'')';
				raise notice 'sql: %', sql;
				execute sql into tmp;
				if (tmp is not null) then
					sql := 'select timestamptz '''||tmp||'''';
					execute sql into curmax;
					stime = curmax;
				end if;
			end if;
			sql := 'select to_char(date_trunc(''month'', timestamptz '''||stime||'''), ''YYYY-MM-DD HH24:MI:SS'')';
			execute sql into tmp;
			sql := 'select extract(epoch from timestamptz '''||tmp||''')';
			execute sql into minval;
			sql := 'select to_char(date_trunc(''month'', timestamptz '''||stime||''') + '''||arr[1]||' months'', ''YYYY-MM-DD HH24:MI:SS'')';
			execute sql into tmp;
			sql := 'select extract(epoch from timestamptz '''||tmp||''')';
			execute sql into maxval;
		when 'y' then
			fmt = 'YYYY';
			if (tmp is not null) then
				sql := 'select regexp_replace('''||tmp||''', ''(\d{4})'', ''\1-01-01 00:00:00'')';
				raise notice 'sql: %', sql;
				execute sql into tmp;
				if (tmp is not null) then
					sql := 'select timestamptz '''||tmp||'''';
					execute sql into curmax;
					stime = curmax;
				end if;
			end if;
			sql := 'select to_char(date_trunc(''year'', timestamptz '''||stime||'''), ''YYYY-MM-DD HH24:MI:SS'')';
			execute sql into tmp;
			sql := 'select extract(epoch from timestamptz '''||tmp||''')';
			execute sql into minval;
			sql := 'select to_char(date_trunc(''year'', timestamptz '''||stime||''') + '''||arr[1]||' years'', ''YYYY-MM-DD HH24:MI:SS'')';
			execute sql into tmp;
			sql := 'select extract(epoch from timestamptz '''||tmp||''')';
			execute sql into maxval;	
	end case;
	
	if (curmax is null) then
		sql := 'select to_char(to_timestamp('''||minval||'''), '''||fmt||''')';
		minval = null;
	else
		sql := 'select to_char(to_timestamp('''||maxval||'''), '''||fmt||''')';
	end if;
	execute sql into name;
	tmp := parent||'_'||name;
    execute create_child_table(parent, tmp, field, minval, maxval, '_default_init_script');
	return tmp;
END;
$$
LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION split_table(
	parent text,
	field text,
	intvl text,
	minval text,
	num integer
)
RETURNS text AS $$
DECLARE
	total integer := 0;
	stime timestamp;
	sql text := '';
BEGIN
	if (minval is null) then
		sql := 'select localtimestamp(0)';
	else
		sql := 'select timestamp '''||minval||'''';
	end if;
	execute sql into stime;
	while (total < num) loop
		perform new_child_table(parent, field, intvl, stime);
		total := total + 1;
	end loop;
	return 'done';
end;
$$
language plpgsql;


select split_table('pb', 'pf', '1m', null, 2);