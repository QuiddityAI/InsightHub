import { defineStore } from "pinia"
import { inject } from "vue"

export const useMapStateStore = defineStore("mapState", {
  state: () => {
    return {
      eventBus: inject("eventBus"),

      passiveMarginsLRTB: [0, 0, 0, 0],

      per_point: {
        cluster_id: [],
        text_data: [],
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
      },

      clusterData: [], // array of cluster description objects
      hover_label_rendering: {},
      textureAtlas: null,
      thumbnailSpriteSize: 64,

      selected_map_tool: "drag", // one of 'drag' or 'lasso'
      selection_merging_mode: "replace", // one of 'replace', 'add', 'remove'
      selected_point_indexes: [],
      visited_point_indexes: [],
      lasso_points: [],
      markedPointIdx: -1,
    }
  },
})
