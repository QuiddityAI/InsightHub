<script setup>
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["statistic"],
  emits: [],
  data() {
    return {
      options: {},
      series: [],
      categories: [],
      category_field: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.create_plot()
    this.eventBus.on("visible_result_ids_updated", () => {
      this.create_plot()
    })
  },
  watch: {
    "appStateStore.map_item_details"(new_val, old_val) {
      this.create_plot()
    },
  },
  methods: {
    create_plot() {
      var begin = new Date().getTime() / 1000;
      const item_details = this.appStateStore.map_item_details

      const y_counts = {}
      const y_values = {}
      for (const ds_and_item_id of this.appStateStore.visible_result_ids) {
        const ds_items = item_details[ds_and_item_id[0]]
        if (!ds_items) continue
        const item = ds_items[ds_and_item_id[1]]

        const categories = this.statistic.x_type === "array_item_category" ? item[this.statistic.x] : [item[this.statistic.x]]
        if (categories === undefined) {
          continue
        }
        for (const category of categories) {
          y_counts[category] = (y_counts[category] || 0) + 1
        }
        for (const y_params of this.statistic.y) {
          const value = y_params.field ? item[y_params.field] : null
          for (const category of categories) {
            if (!y_values.hasOwnProperty(category)) {
              y_values[category] = {}
            }
            y_values[category][y_params.name] = (y_values[category][y_params.name] || 0) + value
          }
        }
      }
      for (const y_params of this.statistic.y) {
        if (y_params.type === "mean") {
          for (const category in y_values) {
            y_values[category][y_params.name] = (y_values[category][y_params.name] / y_counts[category]).toFixed(0)
          }
        }
      }

      const max_columns = this.statistic.max_columns || 20
      let union_of_top_n_categories_per_y = []
      for (const y_params of this.statistic.y) {
        let top_n_categories = []
        if (y_params.type === "mean") {
          top_n_categories = Object.keys(y_counts).sort((a, b) => y_values[b][y_params.name] - y_values[a][y_params.name]).slice(0, max_columns / this.statistic.y.length)
        } else {
          top_n_categories = Object.keys(y_counts).sort((a, b) => y_counts[b] - y_counts[a]).slice(0, max_columns / this.statistic.y.length)
        }
        union_of_top_n_categories_per_y = [...new Set([...union_of_top_n_categories_per_y, ...top_n_categories])]
      }

      // sort categories by mean of all values in each category:
      union_of_top_n_categories_per_y.sort((a, b) => {
        const a_max = Math.max(...Object.values(y_values[a])) / Object.keys(y_values[a]).length
        const b_max = Math.max(...Object.values(y_values[b])) / Object.keys(y_values[b]).length
        return b_max - a_max  // descending
      })
      const categories = union_of_top_n_categories_per_y
      if (this.statistic.order_by === "x") {
        categories.sort()
      }
      this.category_field = this.statistic.x
      this.categories = categories

      const series = []
      for (const y_params of this.statistic.y) {
        series.push({
          name: y_params.name,
          data: y_params.type === "mean" ? categories.map(k => y_values[k][y_params.name] || 0) : categories.map(k => y_counts[k] || 0),
        })
      }

      this.options = {
        xaxis: {
          categories: categories,
        },
        yaxis: {
          show: false,
        },
        tooltip: {  // show tooltip for full height of chart, not only when hovering directly over bar
          shared: true,
          intersect: false
        },
        dataLabels: {  // numbers on bars
          enabled: false,
        },
      }
      this.series = series

      const example_config = {
        "required_fields": [
          "publication_year",
          "cited_by_count",
          "primary_location_name",
          "authors"
        ],
        "groups": [{
          "title": "Year",
          "plots": [{
            "title": "Citations",
            "x": "publication_year",
            "x_type": "category",
            "y": [{"name": "Citations", "field": "cited_by_count", "type": "mean"}, {"name": "# Articles", "field": null, "type": "count"}],
            "order_by": "x",
            "max_columns": 10
            }]
          },
          {
          "title": "Journal",
          "plots": [{
            "title": "Citations",
            "x": "primary_location_name",
            "x_type": "category",
            "y": [{"name": "Citations", "field": "cited_by_count", "type": "mean"}, {"name": "# Articles", "field": null, "type": "count"}],
            "order_by": "y_max",
            "max_columns": 10
            }]
          },
          {
          "title": "Author",
          "plots": [{
            "title": "Citations",
            "x": "authors",
            "x_type": "array_item_category",
            "y": [{"name": "Citations", "field": "cited_by_count", "type": "mean"}, {"name": "# Articles", "field": null, "type": "count"}],
            "order_by": "y_max",
            "max_columns": 10
            }]
          }
        ]
      }

      //console.log(`time to plot: ${(new Date().getTime() / 1000) - begin}`)
    },
    clickHandler(event, chartContext, config) {
      if (config.dataPointIndex === undefined) {
        return
      }
      const category = this.categories[config.dataPointIndex]
      const category_field = this.category_field
      const display_name = `${category_field} = ${category}`
      if (category === undefined) {
        return
      }
      if (this.mapStateStore.visibility_filters.some(filter_item => filter_item.display_name === display_name)) {
        return
      }

      let filter_fn = null
      if (this.statistic.x_type === "array_item_category") {
        filter_fn = (item) => {
          // the category is always stored as a string, so we need to convert the candidates to strings as well
          return item[category_field].map(String).includes(category)
        }
      } else {
        filter_fn = (item) => {
          // the category is always stored as a string, so we need to convert the candidates to strings as well
          return String(item[category_field]) === category
        }
      }

      this.mapStateStore.visibility_filters.push({
        display_name: display_name,
        filter_fn: filter_fn,
      })
      this.eventBus.emit("visibility_filters_changed")
    },
  },
}
</script>

<template>
  <apexchart
    type="bar"
    :options="options"
    :series="series"
    height="220px"
    @click="clickHandler">
  </apexchart>
</template>

<style>
.apexcharts-bar-series {
  cursor: pointer;
}
</style>
