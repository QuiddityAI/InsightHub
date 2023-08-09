<script setup>

</script>

<script>

import { onMounted } from 'vue';
import httpClient from '../api/httpClient';

export default {
  data() {
    return {
      // external:
      passiveMarginsLRTB: [0, 0, 0, 0],
      point_uids: [],
      currentPositionsX: [],
      currentPositionsY: [],
      targetPositionsX: [],
      targetPositionsY: [],
      colors: [],
      sizes: [],
      cluster_ids: [],

      // internal:
      currentVelocityX: [],
      currentVelocityY: [],
      baseScaleX: 1.0,
      baseScaleY: 1.0,
      baseOffsetX: 0.0,
      baseOffsetY: 0.0,
      currentZoom: 1.0,
      targetZoom: 1.0,
      currentPanX: 0.0,
      currentPanY: 0.0,
      targetPanX: 0.0,
      targetPanY: 0.0,
    }
  },
  methods: {
    submit_query(event) {

    }
  },
}

</script>

<template>

  <div class="fixed ring-1 ring-inset ring-gray-300" :style="{'left': passiveMarginsLRTB[0] + 'px', 'right': passiveMarginsLRTB[1] + 'px', 'top': passiveMarginsLRTB[2] + 'px', 'bottom': passiveMarginsLRTB[3] + 'px'}"></div>


</template>

<style scoped></style>
