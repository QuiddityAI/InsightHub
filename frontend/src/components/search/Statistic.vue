<script setup>

import ProgressSpinner from "primevue/progressspinner"

import { debounce } from '../../utils/utils';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store'

import { httpClient } from "../../api/httpClient"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["statistic", "dataset_id", "required_fields"],
  emits: [],
  data() {
    return {
      options: {},
      series: [],
      categories: [],
      category_field: null,
      is_loading: false,
      create_plot_debounced: debounce(() => {
        this.create_plot()
      }, 500),
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.create_plot()
    this.eventBus.on("collection_filters_changed", this.create_plot_debounced)
  },
  unmounted() {
    this.eventBus.off("collection_filters_changed", this.create_plot_debounced)
  },
  watch: {
  },
  methods: {
    create_plot() {
      this.is_loading = true
      const body = {
        collection_id: this.collectionStore.collection_id,
        dataset_id: this.dataset_id,
        statistic_parameters: this.statistic,
        required_fields: this.required_fields,
      }
      httpClient
        .post("/api/v1/filter/get_statistic_data", body)
        .then((response) => {
          this.categories = response.data.categories
          this.options = {
            xaxis: {
              categories: this.categories,
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
          this.series = response.data.series
          this.category_field = this.statistic.x
          this.is_loading = false
        })

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

      const filter_type = this.statistic.x_type === "array_item_category" ? "metadata_value_contains" : "metadata_value_is"

      const filter_uid = `statistic_filter`
      const text_filter = {
        uid: filter_uid,
        display_name: display_name,
        removable: true,
        filter_type: filter_type,
        value: category,
        field: category_field,
      }
      this.collectionStore.add_filter(text_filter)
    },
  },
}
</script>

<template>
  <div>
    <div class="flex flex-col items-center">
      <ProgressSpinner class="h-5 w-5" v-if="is_loading" />
    </div>
    <apexchart
      type="bar"
      :options="options"
      :series="series"
      height="220px"
      @click="clickHandler">
    </apexchart>
  </div>
</template>

<style>
.apexcharts-bar-series {
  cursor: pointer;
}
</style>
