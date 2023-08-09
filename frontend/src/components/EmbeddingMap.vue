<script setup>

</script>

<script>

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
    updateMap() {
      this.baseOffsetX = -Math.min(...this.currentPositionsX)
      this.baseOffsetY = -Math.min(...this.currentPositionsY)
      this.baseScaleX = 1.0 / (Math.max(...this.currentPositionsX) + this.baseOffsetX)
      this.baseScaleY = 1.0 / (Math.max(...this.currentPositionsY) + this.baseOffsetY)
      this.drawCanvas()
    },
    drawCanvas() {
      var canvas = this.$refs.myCanvas;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      var ctx = canvas.getContext("2d");
      const ww = window.innerWidth
      const wh = window.innerHeight
      const activeAreaWidth = ww - this.passiveMarginsLRTB[0] - this.passiveMarginsLRTB[1]
      const activeAreaHeight = wh - this.passiveMarginsLRTB[2] - this.passiveMarginsLRTB[3]
      const px = this.currentPositionsX
      const py = this.currentPositionsY

      for (const i of Array(px.length).keys()) {
        ctx.fillStyle = `hsl(${this.cluster_ids[i] * 36}, 80%, 50%)`
        const relativeX = (px[i] + this.baseOffsetX) * this.baseScaleX  // between 0 - 1
        const relativeY = (py[i] + this.baseOffsetY) * this.baseScaleY  // between 0 - 1
        const finalX = this.passiveMarginsLRTB[0] + (relativeX * activeAreaWidth)
        const finalY = this.passiveMarginsLRTB[2] + (relativeY * activeAreaHeight)
        ctx.fillRect(finalX, finalY, 1, 1);
      }
    },
  },
}

</script>

<template>

  <canvas ref="myCanvas" class="fixed w-full h-full"></canvas>

  <div class="fixed ring-1 ring-inset ring-gray-300" :style="{'left': passiveMarginsLRTB[0] + 'px', 'right': passiveMarginsLRTB[1] + 'px', 'top': passiveMarginsLRTB[2] + 'px', 'bottom': passiveMarginsLRTB[3] + 'px'}"></div>


</template>

<style scoped></style>
