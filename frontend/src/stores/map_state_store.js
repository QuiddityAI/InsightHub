import { defineStore } from "pinia"
import { inject } from "vue"

import { normalizeArrayMedianGamma } from "../utils/utils"

export const useMapStateStore = defineStore("mapState", {
  state: () => {
    return {
      eventBus: inject("eventBus"),
      map_client_x: 0,
      map_client_y: 0,
      map_client_width: 100,
      map_client_height: 100,

      passiveMarginsLRTB: [70, 70, 100, 100],

      map_parameters: null,
      text_data: {},
      answer: null,
      per_point: {
        item_id: [],
        cluster_id: [],
        collection_item_id: [],
        x: [],
        y: [],
        size: [],
        hue: [],
        sat: [],
        val: [],
        opacity: [],
        secondary_hue: [],
        secondary_sat: [],
        secondary_val: [],
        secondary_opacity: [],
        flatness: [],
        thumbnail_aspect_ratio: [],  // aspect ration or -1.0 if no thumbnail
      },

      clusterData: [], // array of cluster description objects
      hover_label_rendering: {},
      textureAtlas: null,
      thumbnailSpriteSize: 64,

      selected_map_tool: "drag", // one of 'drag' or 'lasso'
      selection_merging_mode: "replace", // one of 'replace', 'add', 'remove'
      visited_point_indexes: [],
      lasso_points: [],
      markedPointIdx: -1,
      hovered_point_idx: -1,
      visiblePointIndexes: [],
      show_html_points: false,
      selected_collection_item_ids: [],

      visibility_filters: [], // each filter is an object with keys 'display_name', 'filter_fn' function (item) => bool

      baseScale: [1.0, 1.0],
      baseOffset: [0.0, 0.0],
      baseScaleTarget: [1.0, 1.0],
      baseOffsetTarget: [0.0, 0.0],
      baseScaleVelocity: [0.0, 0.0],
      baseOffsetVelocity: [0.0, 0.0],

      currentZoom: 1.0,
      currentPan: [0.0, 0.0],
    }
  },
  getters: {
    activeAreaWidth() {
      return this.map_client_width - this.passiveMarginsLRTB[0] - this.passiveMarginsLRTB[1]
    },
    activeAreaHeight() {
      return this.map_client_height - this.passiveMarginsLRTB[2] - this.passiveMarginsLRTB[3]
    },
  },
  actions: {
    reset_data() {
      this.text_data = {}
      this.per_point = {
        item_id: [],
        cluster_id: [],
        collection_item_id: [],
        x: [],
        y: [],
        size: [],
        hue: [],
        sat: [],
        val: [],
        opacity: [],
        secondary_hue: [],
        secondary_sat: [],
        secondary_val: [],
        secondary_opacity: [],
        flatness: [],
        thumbnail_aspect_ratio: [],
      }

      this.clusterData = []
      this.textureAtlas = null
      this.thumbnailSpriteSize = 64

      this.markedPointIdx = -1
      this.hovered_point_idx = -1
    },
    // -------------------------------------------------------
    get_item_by_index(index) {
      const [ds_id, item_id] = this.per_point.item_id[index]
      return this.text_data[ds_id][item_id]
    },
    mapLeftFromRelative(x) {
      const normalizedPos = (x + this.baseOffset[0]) * this.baseScale[0]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaWidth + this.passiveMarginsLRTB[0]
      const pannedAndZoomed = shiftedToActiveAreaPos * this.currentZoom + this.currentPan[0]
      return pannedAndZoomed
    },
    mapBottomFromRelative(y) {
      const normalizedPos = (y + this.baseOffset[1]) * this.baseScale[1]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaHeight + this.passiveMarginsLRTB[3]
      const zoomed =
        (shiftedToActiveAreaPos - this.map_client_height) * this.currentZoom + this.map_client_height
      const pannedAndZoomed = zoomed - this.currentPan[1]
      return pannedAndZoomed
    },
    mapRightFromRelative(x) {
      const normalizedPos = (x + this.baseOffset[0]) * this.baseScale[0]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaWidth + this.passiveMarginsLRTB[0]
      const pannedAndZoomed = shiftedToActiveAreaPos * this.currentZoom + this.currentPan[0]
      return this.map_client_width - pannedAndZoomed
    },
    mapTopFromRelative(y) {
      const normalizedPos = (y + this.baseOffset[1]) * this.baseScale[1]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaHeight + this.passiveMarginsLRTB[3]
      const zoomed =
        (shiftedToActiveAreaPos - this.map_client_height) * this.currentZoom + this.map_client_height
      const pannedAndZoomed = zoomed - this.currentPan[1]
      return this.map_client_height - pannedAndZoomed
    },
    screenToEmbeddingX(screenX) {
      const mapX = screenX - this.map_client_x
      const notPannedAndZoomedX = (mapX - this.currentPan[0]) / this.currentZoom
      const notShiftedToActiveAreaX =
        (notPannedAndZoomedX - this.passiveMarginsLRTB[0]) / this.activeAreaWidth
      const notNormalizedX = notShiftedToActiveAreaX / this.baseScale[0] - this.baseOffset[0]
      return notNormalizedX
    },
    screenToEmbeddingY(screenY) {
      const mapY = screenY - this.map_client_y
      const notPannedY = this.map_client_height - mapY + this.currentPan[1]
      const notPannedAndZoomedY =
        (notPannedY - this.map_client_height) / this.currentZoom + this.map_client_height
      const notShiftedToActiveAreaY =
        (notPannedAndZoomedY - this.passiveMarginsLRTB[3]) / this.activeAreaHeight
      const notNormalizedY = notShiftedToActiveAreaY / this.baseScale[1] - this.baseOffset[1]
      return notNormalizedY
    },
    // -------- Visibility Filters & Lasso Selection --------
    reset_visibility_filters() {
      this.visibility_filters = []
      this.eventBus.emit("visibility_filters_changed")
    },
    modify_text_filter(new_text_query, appStateStore) {
      // remove any existing text filter:
      this.visibility_filters = this.visibility_filters.filter(
        (filter_item) => !filter_item.is_text_filter
      )
      if (new_text_query == "") {
        this.eventBus.emit("visibility_filters_changed")
        return
      }
      this.visibility_filters.push({
        display_name: `Contains: "${new_text_query}"`,
        is_text_filter: true,
        hide_remove_button: true,
        text_query: new_text_query,
        filter_fn: (item) => {
          const dataset = appStateStore.datasets[item._dataset_id]
          for (const field of dataset.schema.default_search_fields) {
            const value = item[field]
            const is_string = typeof value === "string" || value instanceof String
            if (value && is_string && value.toLowerCase().includes(new_text_query.toLowerCase())) {
              return true
            }
          }
        }
      })
      this.eventBus.emit("visibility_filters_changed")
    },
    get_lasso_selection() {
      const existing_filter = this.visibility_filters.find(
        (filter_item) => filter_item.is_lasso_selection
      )
      return existing_filter ? existing_filter.selected_point_ids : []
    },
    modify_lasso_selection(ds_and_item_ids, collection_item_ids, mode="replace") {
      // note: as of January 2025, ds_and_item_ids is deprecated and collection_item_ids is used
      // TODO: clean up as soon as its clear that ds_and_item_ids is not used anymore
      const existing_selection = this.get_lasso_selection()
      // remove existing lasso selection filter:
      this.visibility_filters = this.visibility_filters.filter(
        (filter_item) => !filter_item.is_lasso_selection
      )
      if (mode == "replace") {
        // pass
      } else if (mode == "add") {
        ds_and_item_ids = [
          ...new Set([...existing_selection, ...ds_and_item_ids]),
        ]
        collection_item_ids = [
          ...new Set([...this.selected_collection_item_ids, ...collection_item_ids]),
        ]
      } else if (mode == "remove") {
        ds_and_item_ids =
          existing_selection.filter(
            (x) => !ds_and_item_ids.some(selected_id => selected_id[0] == x[0] && selected_id[1] == x[1])
          )
        collection_item_ids =
          this.selected_collection_item_ids.filter(
            (x) => !collection_item_ids.includes(x)
          )
      }
      if (ds_and_item_ids.length == 0) {
        this.eventBus.emit("visibility_filters_changed")
        return
      }
      this.visibility_filters.push({
        display_name: "Lasso Selection",
        is_lasso_selection: true,
        selected_point_ids: ds_and_item_ids,
        filter_fn: (item) => ds_and_item_ids.some(selected_id => selected_id[0] == item._dataset_id && selected_id[1] == item._id),
      })
      this.selected_collection_item_ids = collection_item_ids
      this.eventBus.emit("visibility_filters_changed")
    },
    reset_selection() {
      this.visibility_filters = this.visibility_filters.filter(
        (filter_item) => !filter_item.is_lasso_selection
      )
      this.selected_collection_item_ids = []
      this.eventBus.emit("visibility_filters_changed")
    },
    // ------------------------------------------------------
    set_projection_data(projection_data) {
      if (!projection_data) {
        return this.reset_data()
      }
      this.reset_selection()
      this.per_point.item_id = projection_data.per_point.ds_and_item_id
      this.per_point.x = projection_data.per_point.x
      this.per_point.y = projection_data.per_point.y
      this.per_point.cluster_id = projection_data.per_point.cluster_id
      this.per_point.collection_item_id = projection_data.per_point.collection_item_id
      projection_data.per_point.hue.push(Math.max(...projection_data.per_point.hue) + 1)
      this.per_point.hue = normalizeArrayMedianGamma(
        projection_data.per_point.hue,
        2.0
      ).slice(0, projection_data.per_point.hue.length - 1)
      this.text_data = projection_data.text_data_by_item

      this.eventBus.emit("map_center_and_fit_data_to_active_area_smooth")
      this.eventBus.emit("map_update_geometry")
      this.eventBus.emit("map_reset_pan_and_zoom")
    },
    set_cluster_info(cluster_info) {
      this.clusterData = cluster_info
      this.eventBus.emit("map_update_geometry")
    },
  },
})
