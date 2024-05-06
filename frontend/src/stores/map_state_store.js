import { defineStore } from "pinia"
import { inject } from "vue"

export const useMapStateStore = defineStore("mapState", {
  state: () => {
    return {
      eventBus: inject("eventBus"),

      passiveMarginsLRTB: [0, 0, 0, 0],

      map_parameters: null,
      text_data: {},
      per_point: {
        item_id: [],
        cluster_id: [],
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
      return window.innerWidth - this.passiveMarginsLRTB[0] - this.passiveMarginsLRTB[1]
    },
    activeAreaHeight() {
      return window.innerHeight - this.passiveMarginsLRTB[2] - this.passiveMarginsLRTB[3]
    },
  },
  actions: {
    get_item_by_index(index) {
      const [ds_id, item_id] = this.per_point.item_id[index]
      return this.text_data[ds_id][item_id]
    },
    screenLeftFromRelative(x) {
      const normalizedPos = (x + this.baseOffset[0]) * this.baseScale[0]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaWidth + this.passiveMarginsLRTB[0]
      const pannedAndZoomed = shiftedToActiveAreaPos * this.currentZoom + this.currentPan[0]
      return pannedAndZoomed
    },
    screenBottomFromRelative(y) {
      const normalizedPos = (y + this.baseOffset[1]) * this.baseScale[1]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaHeight + this.passiveMarginsLRTB[3]
      const zoomed =
        (shiftedToActiveAreaPos - window.innerHeight) * this.currentZoom + window.innerHeight
      const pannedAndZoomed = zoomed - this.currentPan[1]
      return pannedAndZoomed
    },
    screenRightFromRelative(x) {
      const normalizedPos = (x + this.baseOffset[0]) * this.baseScale[0]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaWidth + this.passiveMarginsLRTB[0]
      const pannedAndZoomed = shiftedToActiveAreaPos * this.currentZoom + this.currentPan[0]
      return window.innerWidth - pannedAndZoomed
    },
    screenTopFromRelative(y) {
      const normalizedPos = (y + this.baseOffset[1]) * this.baseScale[1]
      const shiftedToActiveAreaPos =
        normalizedPos * this.activeAreaHeight + this.passiveMarginsLRTB[3]
      const zoomed =
        (shiftedToActiveAreaPos - window.innerHeight) * this.currentZoom + window.innerHeight
      const pannedAndZoomed = zoomed - this.currentPan[1]
      return window.innerHeight - pannedAndZoomed
    },
    screenToEmbeddingX(screenX) {
      const notPannedAndZoomedX = (screenX - this.currentPan[0]) / this.currentZoom
      const notShiftedToActiveAreaX =
        (notPannedAndZoomedX - this.passiveMarginsLRTB[0]) / this.activeAreaWidth
      const notNormalizedX = notShiftedToActiveAreaX / this.baseScale[0] - this.baseOffset[0]
      return notNormalizedX
    },
    screenToEmbeddingY(screenY) {
      const notPannedY = window.innerHeight - screenY + this.currentPan[1]
      const notPannedAndZoomedY =
        (notPannedY - window.innerHeight) / this.currentZoom + window.innerHeight
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
          for (const field of dataset.default_search_fields) {
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
    modify_lasso_selection(ds_and_item_ids, mode="replace") {
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
      } else if (mode == "remove") {
        ds_and_item_ids =
          existing_selection.filter(
            (x) => !ds_and_item_ids.some(selected_id => selected_id[0] == x[0] && selected_id[1] == x[1])
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
      this.eventBus.emit("visibility_filters_changed")
    },
    // ------------------------------------------------------
  },
})
