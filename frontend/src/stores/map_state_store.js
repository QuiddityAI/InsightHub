import { defineStore } from "pinia"
import { inject } from "vue"

export const useMapStateStore = defineStore("mapState", {
  state: () => {
    return {
      eventBus: inject("eventBus"),

      passiveMarginsLRTB: [0, 0, 0, 0],

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
  actions: {
    get_item_by_index(index) {
      const [ds_id, item_id] = this.per_point.item_id[index]
      return this.text_data[ds_id][item_id]
    },
  }
})
