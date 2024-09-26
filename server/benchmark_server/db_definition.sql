CREATE TABLE "Command" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "command_name" TEXT NOT NULL UNIQUE,
    "command_content" TEXT NOT NULL
);

CREATE TABLE "ClientConfig" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "config_name" TEXT NOT NULL UNIQUE,
    "config_content" TEXT NOT NULL
);

CREATE TABLE "Metric" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "metric_name" TEXT NOT NULL UNIQUE,
    "metric_description" TEXT NOT NULL
);

CREATE TABLE "CVMFSBuild" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "build_type" TEXT,
    "commit" TEXT NOT NULL UNIQUE,
    "commit_datetime" TEXT NOT NULL,
    "tag" TEXT,
    "version" TEXT NOT NULL
);

CREATE TABLE "BenchmarkResult" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "cvmfs_build_id" INTEGER NOT NULL,
    "command_id" INTEGER NOT NULL,
    "client_config_id" INTEGER NOT NULL,
    "metric_id" INTEGER NOT NULL,
    "cold_cache_min_val" REAL NOT NULL,
    "cold_cache_first_quartile" REAL NOT NULL,
    "cold_cache_median" REAL NOT NULL,
    "cold_cache_third_quartile" REAL NOT NULL,
    "cold_cache_max_val" REAL NOT NULL,
    "warm_cache_min_val" REAL NOT NULL,
    "warm_cache_first_quartile" REAL NOT NULL,
    "warm_cache_median" REAL NOT NULL,
    "warm_cache_third_quartile" REAL NOT NULL,
    "warm_cache_max_val" REAL NOT NULL,
    "hot_cache_min_val" REAL NOT NULL,
    "hot_cache_first_quartile" REAL NOT NULL,
    "hot_cache_median" REAL NOT NULL,
    "hot_cache_third_quartile" REAL NOT NULL,
    "hot_cache_max_val" REAL NOT NULL,
    FOREIGN KEY ("command_id") REFERENCES "Command"("id") ON UPDATE CASCADE,
    FOREIGN KEY ("client_config_id") REFERENCES "ClientConfig"("id") ON UPDATE CASCADE,
    FOREIGN KEY ("metric_id") REFERENCES "Metric"("id") ON UPDATE CASCADE,
    FOREIGN KEY ("cvmfs_build_id") REFERENCES "CVMFSBuild"("id") ON UPDATE CASCADE,
    UNIQUE ("cvmfs_build_id", "command_id", "client_config_id", "metric_id")
);
