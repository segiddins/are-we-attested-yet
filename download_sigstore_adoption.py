import clickhouse_connect
import csv

client = clickhouse_connect.get_client(
    host="sql-clickhouse.clickhouse.com", username="demo", password="", port=443
)

result = client.query("""
with at as (
  select dictGet(rubygems.id_to_name, 'name', rubygem_id) AS name,
    true as has_attestation
  from rubygems.attestations
    left join rubygems.versions on rubygems.attestations.version_id = versions.id
  group by 1
),
  latest as (
    select dictGet(rubygems.id_to_name, 'name', rubygem_id) AS gem,
      max(created_at) as latest_release
    from rubygems.versions
    group by gem
  )
SELECT downloads_per_day.gem as name,
  sum(count) AS total_downloads,
  latest.latest_release,
  has_attestation
FROM rubygems.downloads_per_day
  left join at on at.name = downloads_per_day.gem
  left join latest on latest.gem = downloads_per_day.gem
where toStartOfDay(now()) - interval 1 second >= date
  and date > toStartOfDay(now()) - interval 1 second - interval 30 days
GROUP BY downloads_per_day.gem,
  has_attestation,
  latest.latest_release
having total_downloads >= 1000000
ORDER BY 2 desc
                      """)

with open("sigstore_adoption.csv", "w") as data_file:
    writer = csv.DictWriter(
        data_file,
        fieldnames=[
            "name",
            "total_downloads",
            "latest_release",
            "has_attestation",
        ],
    )
    writer.writeheader()
    for row in result.result_rows:
        writer.writerow(
            {
                "name": row[0],
                "total_downloads": row[1],
                "latest_release": row[2],
                "has_attestation": row[3],
            }
        )
