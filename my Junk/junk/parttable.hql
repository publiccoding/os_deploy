use class10;

create table if not exists parttable(name string, id int ) partitioned by (year int) row format delimited fields terminated by '\t' lines terminated by '\n' stored as textfile;

load data local inpath '${env:HOME}/work/hive_inputs/student1.txt' overwrite into table parttable partition(year='1');

load data local inpath '${env:HOME}/work/hive_inputs/student2.txt' overwrite into table parttable partition(year='2');
